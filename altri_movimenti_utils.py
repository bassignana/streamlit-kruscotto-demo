import logging
import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from decimal import Decimal, getcontext, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta

from config import uppercase_prefixes, technical_fields
from invoice_utils import render_field_widget
from utils import extract_prefixed_field_names, get_standard_column_config, fetch_all_records_from_view

#
#
#
#
# TODO; THERE SHOULD NOT BE ANY MOVEMENT WITHOUT AT LEAST 1 TRANSACTION
# Places where I can add a movement:
# - OK: add button for attivi
# - OK: add button for passivi
# Places where I can delete terms up to 0
# - NOT OK: remove terms attivi  -> inadequate component
# - NOT OK: remove terms passivi -> inadequate component
#
# Also these errors would be easier to catch if I had FK in my db!
#
#
def remove_prefix(col_name, prefixes):
    for prefix in prefixes:
        if col_name.startswith(prefix):
            return col_name[len(prefix):]
    return col_name  # Return original if no prefix found

def validate_payment_terms(payment_terms, total_amount, term_prefix):
    errors = []

    if not payment_terms:
        errors.append("Devi configurare almeno una scadenza di pagamento")
        return False, errors

    # Check total amount matches
    total_configured = sum(Decimal(str(term[term_prefix + 'importo_pagamento'])) for term in payment_terms)
    total_expected = Decimal(str(total_amount))

    if abs(total_configured - total_expected) >= Decimal('0.01'):
        errors.append(f"La somma delle scadenze (€ {total_configured:.2f}) non corrisponde all'importo totale (€ {total_expected:.2f})")

    # Check all amounts are positive
    for i, term in enumerate(payment_terms):
        if term[term_prefix + 'importo_pagamento'] <= 0:
            errors.append(f"L'importo della scadenza {i + 1} deve essere maggiore di zero")

    return len(errors) == 0, errors

def fetch_all_records(supabase_client, table_name: str, user_id: str):
    try:
        result = supabase_client.table(table_name).select('*').eq('user_id', user_id).execute()

        if result.data:
            return result.data
        else:
            return []
    except Exception as e:
        logging.exception(f"Database error in fetch_all_records - error: {e} - table: {table_name}, user_id: {user_id}")
        raise

def are_all_required_fields_present(form_data, sql_table_fields_names, fields_config):
    errors = []
    for field_name, field_config in fields_config.items():
        if field_config.get('required', False) and field_name in sql_table_fields_names:
            value = form_data.get(field_name)
            if not value or (isinstance(value, str) and not value.strip()):
                errors.append(f"Il campo '{field_name}' è obbligatorio")
    return errors

def auto_split_payment_movimenti(importo_totale_documento, num_installments, start_date, term_prefix, interval_days = 30):
    # Precision 28 is different from decimal places!
    # I need to keep high precision to be able to handle float conversion
    # correctly. Then I can use quantize to force decimal places to two.
    getcontext().prec = 28
    MONEY_QUANTIZE = Decimal('0.01')  # 2 decimal places
    CURRENCY_ROUNDING = ROUND_HALF_UP

    def format_money(amount):
        decimal_amount = Decimal(str(amount))
        return decimal_amount.quantize(MONEY_QUANTIZE, rounding=CURRENCY_ROUNDING)

    if num_installments <= 0:
        return []

    total_decimal = format_money(importo_totale_documento)
    amount_per_installment = format_money(total_decimal / num_installments)

    terms = []
    total_allocated = Decimal('0.00')

    for i in range(num_installments):
        # Last installment gets the remainder to avoid rounding errors
        if i == num_installments - 1:
            installment_amount = total_decimal - total_allocated
        else:
            installment_amount = amount_per_installment
            total_allocated += installment_amount

        term = {
            term_prefix + 'data_scadenza': datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=interval_days * (i + 1)),
            term_prefix + 'importo_pagamento': float(installment_amount),
            term_prefix + 'nome_cassa': '',
            term_prefix + 'notes': f'Rata {i + 1} di {num_installments}',
            term_prefix + 'data_pagamento': None  # Not paid yet
        }
        terms.append(term)

    return terms

@st.dialog("Aggiungi un movimento")
def render_add_modal(supabase_client, table_name, fields_config, prefix):

    with st.form(f"add_{table_name}_form",
                 clear_on_submit=True,
                 enter_to_submit=False):

        form_data = {}
        config_items = list(fields_config.items())
        sql_table_fields_names = extract_prefixed_field_names('sql/02_create_tables.sql', prefix)

        # TODO: The use of i % 2 will make so that
        #  if I have two tables with uneven number of fields in the config,
        #  I'll invert the first two fields between the two tables.
        #  I have to use a int(bool_flag) that I will invert at the end of
        #  every insertion.
        cols = st.columns(2)
        for i, (field_name, field_config) in enumerate(config_items):
            with cols[i % 2]:
                if field_name in sql_table_fields_names:
                    form_data[field_name] = render_field_widget(
                        field_name, field_config, key_suffix=f"add_{table_name}"
                    )

        col1, col2 = st.columns([1, 1])

        with col1:
            submitted = st.form_submit_button("Salva", type="primary")

        with col2:
            pass # For space in dialog, for now at least that the dialog is set to dismissable.

        if submitted:
            try:
                errors = are_all_required_fields_present(form_data, sql_table_fields_names, fields_config)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    processed_data = {}
                    for name, value in form_data.items():
                        processed_data[name] = str(value)

                    # When using the rpc function, user_id is added automatically.
                    # processed_data['user_id'] = st.session_state.user.id

                    with st.spinner("Salvataggio in corso..."):

                        try:
                            # I need to ensure to:
                            # 1. Always create a record in the rate_* table
                            # 2. Use a transaction
                            # In order to use the same Postgres function, I need to manually
                            # create the term record. In this record, I don't need to add
                            # special fields like user or *_at because the function and the
                            # triggers will take care of it.
                            #
                            # factor out?
                            MONTHS_IN_ADVANCE = 1
                            data_documento_date = datetime.fromisoformat(processed_data[prefix + 'data'])
                            first_day = datetime(data_documento_date.year, data_documento_date.month, 1)
                            last_day_next_X_months = first_day + relativedelta(months=MONTHS_IN_ADVANCE + 1, days=-1)
                            # terms_due_date = [last_day_next_X_months.date().isoformat()]
                            terms_due_date = last_day_next_X_months.date().isoformat() # Not a list!

                            term = {}
                            if table_name == 'movimenti_attivi':
                                term['rma_numero'] = processed_data['ma_numero']
                                term['rma_data'] = processed_data['ma_data']
                                term['rma_importo_pagamento'] = processed_data['ma_importo_totale']
                                term['rma_data_scadenza'] = terms_due_date
                            elif table_name == 'movimenti_passivi':
                                term['rmp_numero'] = processed_data['mp_numero']
                                term['rmp_data'] = processed_data['mp_data']
                                term['rmp_importo_pagamento'] = processed_data['mp_importo_totale']
                                term['rmp_data_scadenza'] = terms_due_date
                            else:
                                raise Exception("Uniche tabelle supportate: movimenti_attivi, movimenti_passivi.")

                            # DONE; I have two insert_record_fixed functions in the db!
                            #  Remove them, but before save their definition in case I had
                            #  always used the wrong one.
                            # SELECT routine_name, routine_definition
                            # FROM information_schema.routines
                            # WHERE routine_name = 'insert_record_fixed';

                            result = supabase_client.rpc('insert_record_fixed', {
                                'table_name': table_name,
                                'record_data': processed_data,
                                'terms_table_name': 'rate_' + table_name,
                                'terms_data': [term],
                                'test_user_id': None
                            }).execute()

                            if result.data.get('success', False):
                                st.success("Movimento salvato con successo")
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error(f'Error during movement INSERT, result: {result}')
                        except Exception as e:
                            st.error("Error inserting data:", e)

            except Exception as e:
                print(f'Error adding movimento manually: {e}')

@st.dialog("Rimuovi movimento")
def render_delete_modal(supabase_client, table_name, record_id:str):

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Conferma Eliminazione", type="primary",
                     key = table_name + '_delete_modal_button'):
            try:

                with st.spinner("Eliminazione in corso..."):
                    # todo: check this, better error handling
                    # Supabase delete always returns empty data, so we check for no exception
                    result = supabase_client.table(table_name).delete()\
                        .eq('user_id', st.session_state.user.id)\
                        .eq('id', record_id).execute()
                    if result:
                        pass
                    st.success("Movimento eliminato con successo")
                    time.sleep(2)
                    st.rerun()
            except Exception as e:
                raise

    # with col2:
    #     if st.button("🚫 Annulla", use_container_width=True):
    #         st.session_state[f"crud_mode_{table_name}"] = "view"
    #         st.rerun()

@st.dialog("Modifica movimento")
def render_modify_modal(supabase_client, table_name, fields_config, record_data, prefix):

    record_id = record_data['id']
    with st.form(f"modify_{table_name}_form"):
        # form_data will hold the updated value of the form when I click on the
        # Aggiorna button. This is because, for some reason, the code below will rerun
        # and update form_data reading from each widget
        form_data = {}

        config_items = list(fields_config.items())
        sql_table_fields_names = extract_prefixed_field_names('sql/02_create_tables.sql', prefix)

        cols = st.columns(2)
        for i, (field_name, field_config) in enumerate(config_items):
            with cols[i % 2]:
                if field_name in sql_table_fields_names:
                    record_value = record_data.get(field_name, None)
                    form_data[field_name] = render_field_widget(
                        field_name, field_config, record_value,
                        key_suffix=f"modify_{table_name}"
                    )

        col1, col2 = st.columns([1, 1])

        with col1:
            submitted = st.form_submit_button("Aggiorna", type="primary")

        if submitted:
            try:
                errors = are_all_required_fields_present(form_data, sql_table_fields_names, fields_config)
                if errors:
                    for error in errors:
                        st.error(error)

                else:
                    processed_data = {}
                    processed_data['user_id'] = st.session_state.user.id

                    # From the code above, we know that form_data will hold either a value or None,
                    # and we know that if we pass None, the supabase API will convert to NONE or
                    # default value.
                    for name, value in form_data.items():
                        # All string otherwise 'Object of type date is not JSON serializable'
                        processed_data[name] = str(value)

                    with st.spinner("Salvataggio in corso..."):
                        # The addition of .eq() with user_id, is for consistency and safety.
                        # It should not be necessary since ids are unique in the table.
                        result = supabase_client.table(table_name).update(processed_data)\
                            .eq('user_id', st.session_state.user.id)\
                            .eq('id', record_id).execute()

                        # TODO; better error handling
                        if result:
                            st.success("Fattura salvata con successo nel database!")
                            time.sleep(2)
                            st.rerun()
            except Exception as e:
                print(f'Error updating invoice: {e}')
                raise

def to_money(amount):
    getcontext().prec = 28
    MONEY_QUANTIZE    = Decimal('0.01')  # 2 decimal places
    CURRENCY_ROUNDING = ROUND_HALF_UP

    if amount is None:
        decimal_amount = Decimal(0)
    else:
        decimal_amount = Decimal(str(amount))
    return decimal_amount.quantize(MONEY_QUANTIZE, rounding=CURRENCY_ROUNDING)

def money_to_string(amount):

    if not isinstance(amount, Decimal):
        amount = to_money(amount)

    return str(amount)

def auto_split_payment_movement(importo_totale_documento: Decimal, num_installments, start_date,
                                rate_prefix, interval_days = 30):
    # Precision 28 is different from decimal places!
    # I need to keep high precision to be able to handle float conversion
    # correctly. Then I can use quantize to force decimal places to two.

    if num_installments <= 0:
        return []

    total_decimal = to_money(importo_totale_documento)
    amount_per_installment = to_money(total_decimal / num_installments)

    terms = []
    total_allocated = Decimal('0.00')

    for i in range(num_installments):
        # Last installment gets the remainder to avoid rounding errors
        if i == num_installments - 1:
            installment_amount = total_decimal - total_allocated
        else:
            installment_amount = amount_per_installment
            total_allocated += installment_amount
        term = {

            rate_prefix + 'data_scadenza':  datetime.strptime(start_date, '%Y-%m-%d').date() + timedelta(days=interval_days * (i + 1)),
            rate_prefix + 'importo_pagamento': installment_amount,
            rate_prefix + 'nome_cassa': '',
            rate_prefix + 'notes': f'Rata {i + 1} di {num_installments}',
            rate_prefix + 'data_pagamento': None  # Not paid yet
        }
        terms.append(term)

    return terms


def save_movement_terms(edited, terms_key, rate_prefix, importo_totale_movimento, config, movement_key, supabase_client, table_name, backup_terms_key):
    if len(edited) == 0:
        st.warning('Impossibile salvare un movimento senza scadenze di pagamento. '
                   'Inserire delle nuove scadenze o cliccare su Annulla per scartare '
                   'tutte le modifiche apportate')
    else:
        try:
            terms = st.session_state[terms_key]

            # Update terms, cannot do it in a function
            _edited = edited.copy()
            _edited.columns = [rate_prefix + col.replace(' ','_').lower() for col in _edited.columns]
            up_to_date_terms = []
            for k,v in _edited.T.to_dict().items():
                up_to_date_terms.append(v)
            terms = up_to_date_terms


            # Verify total configured
            total_configured = to_money(0)
            for term in terms:
                total_configured += to_money(term[rate_prefix + 'importo_pagamento'])
            total_is_different = importo_totale_movimento != total_configured
            if total_is_different:
                # todo: better formatting of money
                st.warning(f"Differenza di {total_configured - importo_totale_movimento} euro riscontrata tra la somma degli importi delle scadenze configurate e l'importo totale. "
                           f"Correggere prima di proseguire")
                return

            # Verify that all required field are present
            # TODO: I can do a double check with the UI also.
            sql_table_fields_names = extract_prefixed_field_names(
                'sql/02_create_tables.sql',
                rate_prefix)
            for term in terms:
                errors = are_all_required_fields_present(term,
                                                         sql_table_fields_names,
                                                         config)
                if errors:
                    # todo: Better error message
                    st.warning(f'{' '.join(errors)}')
                    return

            # In order to pass all strings and avoid not JSON serializable
            # objects like dates.
            # Todo: i need to create a robust function for this
            terms_to_save = []
            for term in terms:
                new_term = {}
                for k,v in term.items():
                    if v is None:
                        # Otherwise loading the string "None"
                        new_term[k] = v
                    else:
                        new_term[k] = str(v)
                terms_to_save.append(new_term)


            # Avoid to insert the keys of the movement in
            # the session state so I don't have to handle the keys in excess
            # everywhere.
            # Adding movement keys, if missing, for insert.
            for term in terms_to_save:
                for k,v in movement_key.items():
                    if k not in term:
                        term[k] = v

            result = supabase_client.rpc('upsert_terms', {
                'table_name': 'rate_' + table_name,
                'delete_key': movement_key,
                'terms': terms_to_save
            }).execute()

            if result.data.get('success', False):
                st.success("Modifiche eseguite con successo")

                # I've tested it quicly, it seems to work.
                st.session_state[backup_terms_key] = terms

                time.sleep(2)
                st.rerun()
            else:
                st.error(f'Errore nel salvataggio: {result}')

        # todo: fix error management / logging.
        #  Here is interesting because the above catches db error that are not
        #  exceptions, the below only exceptions.
        except Exception as e:
            st.error(f"Eccezione nel salvataggio: {str(e)}")

# def create_save_callback(edited, terms_key, rate_prefix, importo_totale_movimento,
#                          config, movement_key, supabase_client, table_name, backup_terms_key):
#     def callback():
#         save_movement_terms(edited, terms_key, rate_prefix, importo_totale_movimento,
#                             config, movement_key, supabase_client, table_name, backup_terms_key)
#     return callback

def render_movimenti_crud_page(supabase_client, user_id,
                               table_name, prefix,
                               rate_prefix,
                               config):

    terms_key = table_name + '_terms'
    backup_terms_key = table_name + '_backup_terms'
    selection_key = table_name + table_name + '_selected_movement'

    # Selected movement is only used for knowing when to refetch data
    # from the terms table when the user changes selection.
    if selection_key not in st.session_state:
        st.session_state[selection_key] = None

    if terms_key not in st.session_state:
        st.session_state[terms_key] = None

    # This is for managing the 'Annulla' button
    # It will just store the first version fetched from the database.
    # The only two place where this is set should be:
    # After a successful save
    # When I change selection in the dataframe, the backup terms must correspond
    # to the terms of the new selection.
    if backup_terms_key not in st.session_state:
        st.session_state[backup_terms_key] = None

    # movimenti_data = fetch_all_records(supabase_client, table_name, user_id)
    movimenti_data = fetch_all_records_from_view(supabase_client, table_name + '_overview')

    if not movimenti_data:
        st.warning("Nessun movimento trovato. Creare un movimento prima di proseguire.")
        add = st.button("Aggiungi Movimento", type='primary', key = table_name + '_add_first_movement')
        if add:
            render_add_modal(supabase_client, table_name,
                             config,
                             prefix)
        return

    df = pd.DataFrame(movimenti_data)
    df.columns = [
        col.replace('_', ' ').title() if isinstance(col, str) else str(col)
        for col in df.columns
    ]

    for tech_field in technical_fields:
        if tech_field in df.columns:
            df = df.drop([tech_field], axis = 1)
    df.columns = [remove_prefix(col, uppercase_prefixes) for col in df.columns]

    def format_italian_currency(val):
        """Italian currency: 1.250,50"""
        if pd.isna(val):
            return "0,00"
        formatted = f"{val:,.2f}"
        formatted = formatted.replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')
        return f"{formatted}"

    # df = df.style.format({
    #     'Importo Totale': format_italian_currency,
    # })

    selection = st.dataframe(df, use_container_width=True,
                             selection_mode = 'single-row',
                             on_select='rerun',
                             hide_index = True,
                             key = table_name + 'selection_df')


    col1, col2, col3, space = st.columns([1,1,1,4])
    with col1:
        add = st.button("Aggiungi Movimento", type='primary', key = table_name + '_add')
        if add:
            render_add_modal(supabase_client, table_name,
                             config,
                             prefix)

    with col2:
        modify = st.button("Modifica Movimento", key = table_name + '_modify')
        if modify:
            if selection.selection['rows']:
                selected_index = selection.selection['rows'][0]
                selected_row = movimenti_data[selected_index]
                render_modify_modal(supabase_client, table_name,
                                    config, selected_row, prefix)
            else:
                st.warning('Seleziona un movimento da modificare')

    with col3:
        delete = st.button("Rimuovi Movimento", key = table_name + '_delete')
        if delete:
            if selection.selection['rows']:
                selected_index = selection.selection['rows'][0]
                selected_id = movimenti_data[selected_index]['id']
                render_delete_modal(supabase_client, table_name, selected_id)
            else:
                st.warning('Seleziona un movimento da eliminare')


    # Here I fetch data to be sure to have the most up to date data,
    # but in the future this might be simplified.
    check_movimenti = fetch_all_records(supabase_client, table_name, user_id)
    check_terms = pd.DataFrame(fetch_all_records(supabase_client, 'rate_' + table_name, user_id))

    for mov in check_movimenti:

        number_key = mov[prefix + 'numero']
        date_key = mov[prefix + 'data']

        m_terms = check_terms[(check_terms[rate_prefix + 'numero'] == number_key) & \
                              (check_terms[rate_prefix + 'data'] == date_key)]


        total_m = mov[prefix + 'importo_totale']
        total_m_terms = m_terms[rate_prefix + 'importo_pagamento'].sum()

        if total_m != total_m_terms:
            st.warning(f'ATTENZIONE: Il movimento numero {number_key}, in data {date_key} ha un importo '
                       f'totale di {total_m} Euro, mentre le relative scadenze hanno un importo '
                       f'totale di {total_m_terms} Euro. Assicurarsi di far combaciare gli importi')

    with st.expander("Visualizza e Gestisci Scadenze"):
        # TODO: In order to help the user understand that the rows of the dataframe can be clicked,
        #  start with the first checkbox selected,
        #  or at least visible by default
        #  or at least give a label to the selection column.

        if selection.selection['rows']:

            selected_index = selection.selection['rows'][0]

            # selected row
            record_data = movimenti_data[selected_index]

            st.write(record_data)

            importo_totale_movimento = to_money(record_data[prefix + 'importo_totale'])
            numero_documento = record_data[prefix + 'numero']
            data_documento   = record_data[prefix + 'data']
            movement_key = {
                rate_prefix + 'numero': numero_documento,
                rate_prefix + 'data': data_documento
            }

            if st.session_state[terms_key] is None or st.session_state[selection_key] != selection:
                try:
                    result = supabase_client.table('rate_' + table_name).select('*').eq('user_id', user_id) \
                        .eq(rate_prefix + 'numero', record_data[prefix + 'numero']) \
                        .eq(rate_prefix + 'data', record_data[prefix + 'data']).execute()

                    existing_terms = []
                    for row in result.data:
                        term = {
                            rate_prefix + 'data_scadenza': datetime.strptime(row[rate_prefix + 'data_scadenza'], '%Y-%m-%d').date(),
                            rate_prefix + 'data_pagamento': datetime.strptime(row[rate_prefix + 'data_pagamento'], '%Y-%m-%d').date() if row[rate_prefix + 'data_pagamento'] else None,
                            rate_prefix + 'importo_pagamento': float(row[rate_prefix + 'importo_pagamento']),
                            rate_prefix + 'nome_cassa': row[rate_prefix + 'nome_cassa'] or '',
                            rate_prefix + 'notes': row[rate_prefix + 'notes'] or '',
                        }
                        existing_terms.append(term)
                    st.session_state[terms_key] = existing_terms
                    st.session_state[selection_key] = selection
                    # This try should be triggered only on the first loading or when I change selection
                    # so it should be safe to reset the existing terms here.
                    st.session_state[backup_terms_key] = existing_terms
                except Exception as e:
                    st.error(f"Errore nel caricamento dei termini: {str(e)}")

            # st.write(st.session_state[terms_key])
            terms_df = pd.DataFrame(st.session_state[terms_key])
            terms_df.columns = [col[len(rate_prefix):].replace('_',' ').title() for col in terms_df.columns]

            # Since some dates can be valued as None, ensure that the date columns
            # are correctly represented as dates.
            date_columns = ['Data Scadenza', 'Data Pagamento']
            money_columns = ['Importo Pagamento']
            for col in date_columns:
                # This is the correct way to convert a possibly Null column, interpreted
                # as a string by pandas to a datetime.date data format while keeping None
                # instead of NaT.
                # Using the commented out versions gives Timestamp format (1) or creates NaT (2).
                # Then the terms in the session state will be Timestamp, and NaT are not read
                # by the database, so it will raise an error.
                # terms_df[col] = pd.to_datetime(terms_df[col], format='%Y-%m-%d')
                # terms_df[col] = pd.to_datetime(terms_df[col]).dt.date
                terms_df[col] = terms_df[col].apply(lambda x: None if x is None or pd.isna(x) else pd.to_datetime(x).date())


            column_config = get_standard_column_config(money_columns = money_columns,
                                                       date_columns = date_columns)

            column_config['Nome Cassa'] = st.column_config.SelectboxColumn(
                "Nome Cassa",
                options=[ # TODO; fix casse
                    "Cassa 1",
                    "Cassa 2",
                    "Cassa 3"
                ],
                required=False)

            # TODO; fix column name
            column_config['Notes'] = st.column_config.TextColumn(
                "Notes",
                required=False)


            terms_df = terms_df.style.format({
                'Importo Pagamento': format_italian_currency,
            })

            st.write('Scadenze in modifica:')

            # TODO: add column ordering, otherwise it changes sometimes.
            # editing_enabled = st.toggle('Modifica Tabella', key = table_name + '_toggle')
            # st.write(st.session_state[table_name + '_toggle'])

            # edited = st.data_editor(terms_df,
            #                         key = table_name + '_terms_df',
            #                         column_config = column_config,
            #                         hide_index = True,
            #                         num_rows = 'dynamic',
            #                         # disabled=not editing_enabled,
            #                         )

            @st.fragment
            def payment_terms_editor(terms_df, column_config, table_name):
                """Isolated fragment for the data editor, otherwise the first
                    save click does not work!"""
                return st.data_editor(terms_df,
                                      key=table_name + '_terms_df',
                                      column_config=column_config,
                                      hide_index=True,
                                      num_rows='dynamic')

            edited = payment_terms_editor(terms_df, column_config, table_name)

            c1, c2,  c3, c4 = st.columns([3,3,1,1], vertical_alignment='top')

            with c1:
                with st.expander("Configurazione Iniziale Rapida", width=500):
                    st.write("""La configurazione rapida permette di generare automaticamente il
                                    numero desiderato di scadenze con importo diviso ugualmente.""")
                    st.write("""Attenzione: questa operazione sovrascriverà tutti i campi delle
                                    scadenze attualmente configurate.""")
                    split_col1, split_col2, split_col3 = st.columns([1, 1, 1],
                                                                    vertical_alignment='bottom')

                    with split_col1:
                        num_installments = st.number_input("Numero rate", min_value=1, max_value=12, value=1,
                                                           key = table_name + '_num_installments')

                    with split_col2:
                        interval_days = st.number_input("Giorni tra rate", min_value=1, max_value=365, value=30, step=15,
                                                        key = table_name + '_interval_days')

                    with split_col3:
                        # TODO; can I put an help message over the button
                        #  so that I don't have to handle the complexity of a dialog?
                        if st.button("Applica", key = table_name + '_apply_rapid_config'):

                            up_to_date_terms = auto_split_payment_movement(
                                importo_totale_movimento, num_installments, data_documento, rate_prefix, interval_days
                            )
                            st.session_state[terms_key] = up_to_date_terms
                            st.rerun()
            with c2:
                with st.expander("Divisione Automatica Importo", width=500):

                    # Since streamlit does not support the features that I need to ensure that there
                    # is always present at least one term,
                    # for now an if statement before every element will do.
                    if len(edited) == 0:
                        st.warning('Creare almeno una scadenza prima di procedere')
                    else:
                        _edited = edited.copy()
                        _edited.columns = [rate_prefix + col.replace(' ','_').lower() for col in _edited.columns]

                        up_to_date_terms = []
                        for k,v in _edited.T.to_dict().items():
                            up_to_date_terms.append(v)

                        total_decimal          = to_money(importo_totale_movimento)
                        movements_count        = len(up_to_date_terms)
                        amount_per_installment = to_money(total_decimal / movements_count)

                        st.write("""La a divisione automatica permette di dividere l'importo totale in parti uguali
                                        nelle rate attualmente presenti. Gli altri campi resteranno invariati.""")
                        st.write(f"""Con la configurazione attuale si otterrebbero
                                        {movements_count} rate da {amount_per_installment} Euro ciascuna.""")

                        if st.button("Dividi Importo", key = table_name + '_apply_auto_config'):

                            total_allocated = Decimal('0.00')

                            for i in range(movements_count):
                                # Last installment gets the remainder to avoid rounding errors
                                if i == movements_count - 1:
                                    up_to_date_terms[i][rate_prefix + 'importo_pagamento'] = total_decimal - total_allocated
                                else:
                                    up_to_date_terms[i][rate_prefix + 'importo_pagamento'] = amount_per_installment
                                    total_allocated += amount_per_installment

                            st.session_state[terms_key] = up_to_date_terms
                            st.rerun()
            with c3:
                save = st.button("Salva  ", type='primary', key = table_name + '_save_terms', use_container_width=True)
                if save:
                    save_movement_terms(edited, terms_key, rate_prefix, importo_totale_movimento,
                                        config, movement_key, supabase_client, table_name, backup_terms_key)


            with c4:
                if st.button('Annulla', key = table_name + '_cancel_terms', use_container_width=True):

                    # NOTE IMPORTANT: for some reason, if I do
                    # st.session_state[terms_key] = st.session_state[backup_terms_key],
                    # the rerun() does not trigger the recomputing of the terms_df.
                    # I have to use a variable like undo_terms!
                    undo_terms = st.session_state[backup_terms_key]
                    st.session_state[terms_key] = undo_terms
                    st.rerun()
        else:
            st.warning('Seleziona un movimento per gestirne le rate')