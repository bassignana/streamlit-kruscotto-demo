import traceback

import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from decimal import Decimal, getcontext, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta
from config import uppercase_prefixes, technical_fields, ma_tipo_options, mp_tipo_options
from invoice_utils import render_field_widget
from utils import extract_prefixed_field_names, get_standard_column_config, fetch_all_records_from_view, \
    fetch_record_from_id, to_money, are_all_required_fields_present, remove_prefix, fetch_all_records, \
    format_italian_currency


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

@st.dialog("Aggiungi movimento")
def render_add_modal(supabase_client, table_name, fields_config, prefix):

    with st.form(f"add_{table_name}_form",
                 clear_on_submit=False,
                 enter_to_submit=False):

        form_data = {}
        config_items = list(fields_config.items())
        sql_table_fields_names = extract_prefixed_field_names('sql/02_create_tables.sql', prefix)

        # TODO: The use of i % 2 will make so that
        #  if I have two tables with uneven number of fields in the config,
        #  I'll invert the first two fields between the two tables.
        #  I have to use a int(bool_flag) that I will invert at the end of
        #  every insertion.
        # for i, (field_name, field_config) in enumerate(config_items):
        #     with cols[i % 2]:
        #         if field_name in sql_table_fields_names:
        #             form_data[field_name] = render_field_widget(
        #                 field_name, field_config, key_suffix=f"add_{table_name}"
        #             )

        cols = st.columns(2)
        column_flag = False  # Start with left column (index 0)
        for i, (field_name, field_config) in enumerate(config_items):
            with cols[int(column_flag)]:
                if field_name in sql_table_fields_names:
                    form_data[field_name] = render_field_widget(
                        field_name, field_config, key_suffix=f"add_{table_name}"
                    )
                    # Only invert the flag after actually rendering a field
                    column_flag = not column_flag

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
                        return
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
                            last_day_next_X_months = first_day + relativedelta(months=MONTHS_IN_ADVANCE, days=-1)
                            # terms_due_date = [last_day_next_X_months.date().isoformat()]
                            terms_due_date = last_day_next_X_months.date().isoformat() # Not a list!

                            term = {}
                            if table_name == 'movimenti_attivi':
                                term['rma_numero'] = processed_data['ma_numero']
                                term['rma_data'] = processed_data['ma_data']
                                term['rma_importo_pagamento'] = processed_data['ma_importo_totale']
                                term['rma_data_scadenza'] = processed_data['ma_data']
                            elif table_name == 'movimenti_passivi':
                                term['rmp_numero'] = processed_data['mp_numero']
                                term['rmp_data'] = processed_data['mp_data']
                                term['rmp_importo_pagamento'] = processed_data['mp_importo_totale']
                                term['rmp_data_scadenza'] = processed_data['mp_data']
                            else:
                                raise Exception("Uniche tabelle supportate: movimenti_attivi, movimenti_passivi.")

                            # DONE; I have two insert_record_fixed functions in the db!
                            #  Remove them, but before save their definition in case I had
                            #  always used the wrong one.
                            # SELECT routine_name, routine_definition
                            # FROM information_schema.routines
                            # WHERE routine_name = 'insert_record_fixed';

                            result = supabase_client.rpc('insert_record', {
                                'table_name': table_name,
                                'record_data': processed_data,
                                'terms_table_name': 'rate_' + table_name,
                                'terms_data': [term],
                                'test_user_id': None
                            }).execute()

                            if result.data.get('success', False):
                                st.success("Movimento salvato con successo")
                                st.rerun()
                            else:
                                st.error(f'Error during movement INSERT, result: {result}')
                        except Exception as e:
                            st.error("Error inserting data:", e)

            except Exception as e:
                print(f'Error adding movimento manually: {e}')

@st.dialog("Rimuovi movimento")
def render_delete_modal(supabase_client, table_name, record_id):

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Conferma Eliminazione", type="primary",
                     key = table_name + '_delete_modal_button'):
            try:
                with st.spinner("Eliminazione in corso..."):

                    # Supabase delete always returns empty data, so we check for no exception
                    result = supabase_client.table(table_name).delete() \
                        .eq('user_id', st.session_state.user.id) \
                        .eq('id', record_id).execute()

                    has_errored = (hasattr(result, 'error') and result.error)

                    if not has_errored:
                        # To delete terms when I delete movements for now I'll use just the
                        # CASCADE clause. In the future I might use an ad hoc transaction to
                        # make the system more robust to sql definition errors.

                        st.success("Dati eliminati con successo!")
                        st.rerun()

                    else:
                        st.error(f"Errore rimozione movimento: {result.error.message}")
                        return

            except Exception as e:
                raise Exception(f'Error deleting movement: {e}')


@st.dialog("Modifica movimento")
def render_modify_modal(supabase_client, table_name, fields_config, selected_id, prefix):
    # """
    # Infrastruttura:
    # scelgo di scaricare solo una vista, che deve pero' avere, necessariamente, i riferimenti all'id
    # di almeno una tabella padre che mi permetta di fare fetch dei dati appena mi servono, partendo
    # dalle tabelle tecniche.
    # In questo modo faro' molte piu' query, ma almeno avro' sempre dati up to date e non dovro'
    # gestire un oggetto che sara' immediatamente out of sync appena cambia qualcosa.
    # Inoltre, soprattutto in streamlit, se faccio tanti rerun e l'utente ha tanti dati, evito
    # di scaricare tante volte tabelle 'pesanti'.
    #
    # Inoltre, se usassi l'id come index nelle visualizzazioni?
    # """

    selected_row_parent_data = fetch_record_from_id(supabase_client, table_name, selected_id)

    with st.form(f"modify_{table_name}_form",
                 clear_on_submit=False,
                 enter_to_submit=False):
        # form_data will hold the updated value of the form when I click on the
        # Aggiorna button. This is because, for some reason, the code below will rerun
        # and update form_data reading from each widget
        form_data = {}

        config_items = list(fields_config.items())
        sql_table_fields_names = extract_prefixed_field_names('sql/02_create_tables.sql', prefix)

        # This is weird to manage. Right now, I'm passing the row taken from the view.
        # The result is that if the prefix are the same, then the value is displayed, else
        # it is an empty field.
        # This is because with this architecture I need to think that I can only update easily full technical
        # tables but not views.
        cols = st.columns(2)
        for i, (field_name, field_config) in enumerate(config_items):
            with cols[i % 2]:
                if field_name in sql_table_fields_names:
                    record_value = selected_row_parent_data.get(field_name, None)
                    # Since in their infinite intelligence they decided that for selecting a value
                    # from the dropdown menu I need to pass its index, instead of the value itself(!),
                    # I need to add this branch.
                    if field_name == 'ma_tipo':
                        form_data[field_name] = render_field_widget(
                            field_name, field_config, index=ma_tipo_options.index(record_value),
                            key_suffix=f"modify_{table_name}"
                        )
                    elif field_name == 'mp_tipo':
                        form_data[field_name] = render_field_widget(
                            field_name, field_config, index=mp_tipo_options.index(record_value),
                            key_suffix=f"modify_{table_name}"
                        )
                    else:
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
                            .eq('id', selected_id).execute()

                        has_errored = (hasattr(result, 'error') and result.error)

                        if not has_errored:
                            st.success("Dati modificati con successo!")
                            st.rerun()
                        else:
                            st.error(f"Errore modifica dati: {result.error.message}")
                            return

            except Exception as e:
                print(f'Error updating invoice: {e}')
                raise

def auto_split_payment_movement(importo_totale_documento: Decimal, num_installments, start_date,
                                rate_prefix, interval_days = 30):
    """
    In theory this is for initializing a new set of terms, but since users will use this to add things fast
    to already initialized movements.
    I tried to preserve current_terms information as much as possible but it cannot be done since I will
    not know where to insert the new terms.
    """


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
            'id':None,
            rate_prefix + 'data_scadenza':  datetime.strptime(start_date, '%Y-%m-%d').date() + timedelta(days=interval_days * (i + 1)),
            rate_prefix + 'importo_pagamento': installment_amount,
            rate_prefix + 'display_cassa': '',
            rate_prefix + 'notes': f'Rata {i + 1} di {num_installments}',
            rate_prefix + 'data_pagamento': None,  # Not paid yet
            rate_prefix + 'fattura_attesa': 'Nessuna'
        }
        terms.append(term)

    return terms

def save_movement_terms(edited, terms_key, rate_prefix, importo_totale_movimento,
                        config, movement_key, supabase_client, table_name,
                        backup_terms_key, are_terms_updated):
    if len(edited) == 0:
        st.warning('Impossibile salvare un movimento senza scadenze di pagamento. '
                   'Inserire delle nuove scadenze o cliccare su Annulla per scartare '
                   'tutte le modifiche apportate')
    else:
        try:

            _edited = edited.copy()
            _edited.columns = [rate_prefix + col.replace(' ','_').lower() for col in _edited.columns]
            _edited = _edited.rename(columns={rate_prefix + 'id': 'id'})
            # are_all_ids_none = _edited['id'].isna().all()

            up_to_date_terms = []
            for k,v in _edited.T.to_dict().items():
                up_to_date_terms.append(v)
            terms = up_to_date_terms
            
            # Verify total configured
            # TODO; This does not work at first try
            total_configured = to_money(0)
            for term in terms:
                total_configured += to_money(term[rate_prefix + 'importo_pagamento'])
            total_is_different = importo_totale_movimento != total_configured
            if total_is_different:
                # todo: better formatting of money
                st.warning(f"Differenza di {total_configured - importo_totale_movimento} euro riscontrata tra la somma degli importi delle scadenze configurate e l'importo totale. "
                           f"Correggere prima di proseguire")
                return

            # Avoid to insert the keys of the movement in
            # the session state so I don't have to handle the keys in excess
            # everywhere.
            # Adding movement keys, if missing, for insert.
            terms_to_save = []

            # In order to pass all strings and avoid not JSON serializable
            # objects like dates.
            for term in terms:
                new_term = {}
                for k,v in term.items():
                    if v is None:
                        # Otherwise loading the string "None"
                        new_term[k] = v
                    else:
                        new_term[k] = str(v)
                terms_to_save.append(new_term)

            # Adding movement keys, if missing, for insert.
            for term in terms_to_save:
                for k,v in movement_key.items():
                    if k not in term:
                        term[k] = v

            # Verify that all required field are present
            sql_table_fields_names = extract_prefixed_field_names(
                'sql/02_create_tables.sql',
                rate_prefix)
            # NOTE: this is a hack! the prefix here is rm*_, but in the config there is only m*_
            # type prefix.
            # correct_sql_fields = [field[1:] for field in sql_table_fields_names]
            # correct_terms = []
            # for term in terms:
            #     correct_term = {}
            #     for k,v in term.items():
            #         correct_term[k[1:]] = v
            #     correct_terms.append(correct_term)

            errors = []
            for term in terms_to_save:
                errors.append(are_all_required_fields_present(term,
                                                         sql_table_fields_names,
                                                         config))
            if any(errors):
                for error in errors:
                    # todo: Better error message
                    st.warning(f'{' '.join(error)}')
                return

            for i in range(len(terms_to_save)):
                term = terms_to_save[i]

                term.pop(rate_prefix + 'x', None)

                row_id = term['id']
                if row_id:
                    result = supabase_client.table('rate_' + table_name).select('*') \
                        .eq('id', row_id) \
                        .eq('user_id', st.session_state.user.id).execute()
                    
                    nome = result.data[0].get(rate_prefix + 'nome_cassa')
                    iban = result.data[0].get(rate_prefix + 'iban_cassa')
                    term[rate_prefix + 'nome_cassa'] = nome
                    term[rate_prefix + 'iban_cassa'] = iban

            result = supabase_client.rpc('upsert_terms', {
                'table_name': 'rate_' + table_name,
                'delete_key': movement_key,
                'terms': terms_to_save
            }).execute()
            
            if result.data.get('success', False):
                st.success("Modifiche eseguite con successo")

                st.session_state[backup_terms_key] = terms

                # TODO: if the above works, maybe i can just update the terms here instead of fetching them twice.
                #  I have to just remove all the state are_terms_updated and assign the new terms to the current terms key
                st.session_state[are_terms_updated] = True
                
                st.rerun()
            else:
                st.error(f'Errore nel salvataggio: {result}')
                st.text("Stack trace:")
                st.text(traceback.format_exc())

        # todo: fix error management / logging.
        #  Here is interesting because the above catches db error that are not
        #  exceptions, the below only exceptions.
        except Exception as e:
            st.error(f"Eccezione nel salvataggio: {str(e)}")
            st.text("Stack trace:")
            st.text(traceback.format_exc())

def render_movimenti_crud_page(supabase_client, user_id,
                               table_name, prefix,
                               rate_prefix,
                               config):
    """
    OLD ------------------------------------------------------------------------------------------------
    Unificare formato dati:
    - se una vista riporta campi presi da una tabella, il prefisso deve restare quello
      della tabella originale, forse se un campo invece e' calcolato, si puo' vedere se mettere il
      prefisso v_ o meno.
    - deve esserci una chiara distinzione della parte del codice che lavora con i dati da quella che li
      visualizza: lavoro con i prefissi e visualizzo senza i prefissi, pero' la rimozione dei prefissi deve
      avvenire unicamente in sede di visualizzazione. Anzi, sarebbe buono se la cosa fosse fatta solo tramite
      column config, in modo da lavorando dando per scontato che ci sono i prefissi.
    - a questo punto potrei provare a mettere v_ e gestirlo nei column config

    NOTE: if I need, in the view I can get the id of the primary table also to delete rows easily
    OLD ------------------------------------------------------------------------------------------------

    Formato dati:
    - If I crud over a parent table without views, I have the table loaded and all names are
      what would I expect, with the right prefixes and everything.
    - If I crud over a view:
    -- The view has to have an id of a parent table with witch I can query the original records
       when I need them on the spot.
    --? The view has to have a v_ prefix for all fields that are not a 1:1 copy of the parents'
    -- The visualization of the view has to make sure to not suggest to edit a field that is a v_
       composite field. In that case I have to tell the user how to do it or just create a custom form.
    --? Keep two copies of the data: the data fetched for the view, and the processed data for the visualization.

    -- MAYBE all of this is too restrictive, in a particular section I have to just make sure that
       I keep the naming and the data that I'm working with consistent just within that section,
       especially if that section interacts with the db only and not with other aspects of the app.

    >>   For sure, now just finish the app.

    """
    terms_key = table_name + '_terms'
    backup_terms_key = table_name + '_backup_terms'
    selection_key = table_name + table_name + '_selected_movement'
    are_terms_updated = table_name + '_are_terms_updated'

    # Selected movement is only used for knowing when to refetch data
    # from the terms table when the user changes selection.
    if selection_key not in st.session_state:
        st.session_state[selection_key] = None

    if terms_key not in st.session_state:
        st.session_state[terms_key] = None

    # TODO: can I just refetch data from the db when I click the
    #  button so that I don't have to manage extra state?
    # This is for managing the 'Annulla' button
    # It will just store the first version fetched from the database.
    # The only two place where this is set should be:
    # After a successful save
    # When I change selection in the dataframe, the backup terms must correspond
    # to the terms of the new selection.
    if backup_terms_key not in st.session_state:
        st.session_state[backup_terms_key] = None

    # This is for rerunning the piece of code that will update the terms that go into the
    # terms df viewer after having saved them into the database.
    if are_terms_updated not in st.session_state:
        st.session_state[are_terms_updated] = False




    # For now it is impossible to have anomalie in altri movimenti.
    # check_movimenti = fetch_all_records(supabase_client, table_name, user_id)
    # check_terms = pd.DataFrame(fetch_all_records(supabase_client, 'rate_' + table_name, user_id))
    # anomalies = {}
    # for mov in check_movimenti:
    #
    #     number_key = mov[prefix + 'numero']
    #     date_key = mov[prefix + 'data']
    #
    #     m_terms = check_terms[(check_terms[rate_prefix + 'numero'] == number_key) & \
    #                           (check_terms[rate_prefix + 'data'] == date_key)]
    #
    #
    #     total_m = to_money(mov[prefix + 'importo_totale'])
    #     total_m_terms = to_money(m_terms[rate_prefix + 'importo_pagamento'].sum())
    #
    #     if total_m != total_m_terms:
    #         anomalies[number_key] = (f'ANOMALIA: Il movimento numero {number_key}, in data {date_key} ha un importo '
    #                    f'totale di {total_m} Euro, mentre le relative scadenze hanno un importo '
    #                    f'totale di {total_m_terms} Euro. Assicurarsi di far combaciare gli importi')
    #





    movimenti_data = fetch_all_records_from_view(supabase_client, table_name + '_overview')

    if not movimenti_data:
        st.warning("Nessun movimento trovato. Creare un movimento prima di proseguire.")
        add = st.button("Aggiungi Movimento", type='primary', key = table_name + '_add_first_movement')
        if add:
            render_add_modal(supabase_client, table_name,
                             config,
                             prefix)
        return

    else:
        #
        #
        # Here is the problem, I either create two dataframe, one with original names and
        # one for visualizations with customized column names or I use the data list instead of the df
        # to work with original names.
        #
        #
        df_vis = pd.DataFrame(movimenti_data)
        df_vis = df_vis.set_index('id')
        df_vis.columns = [
            col.replace('_', ' ').title() if isinstance(col, str) else str(col)
            for col in df_vis.columns
        ]

        for tech_field in technical_fields:
            if tech_field in df_vis.columns:
                df_vis = df_vis.drop([tech_field], axis = 1)
        df_vis.columns = [remove_prefix(col, uppercase_prefixes) for col in df_vis.columns]

        # For now it is impossible to have anomalie in altri movimenti.
        # df_vis['Anomalie'] = df_vis['Numero'].apply(lambda x: 'Presenti' if x in anomalies else 'No')

        if table_name == 'movimenti_attivi':
            money_columns = ['Importo Totale', 'Incassato', 'Saldo']
        elif table_name == 'movimenti_passivi':
            money_columns = ['Importo Totale', 'Pagato', 'Saldo']
        else:
            raise Exception("Column identification: wrong table name?")

        column_config = {}
        for col in df_vis.columns:
            if col in money_columns:
                column_config[col] = st.column_config.NumberColumn(
                    label=col,
                    format="accounting",
                )

        df_vis = df_vis.sort_values(by = ['Data', 'Numero'])

        selection = st.dataframe(df_vis, use_container_width=True,
                                 selection_mode = 'single-row',
                                 on_select='rerun',
                                 hide_index = True,
                                 column_config=column_config,
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
                    # BAD: Here I'm relying on the fact that the index in the df and
                    # in the movimenti_data state will always be in sync.
                    #
                    # When selection is active, only selection is returned, but the index
                    # returned will always refer to the original data passed as input to
                    # st.dataframe and not the current sorting of the dataframe.
                    # So to be sure to manage order correctly, is better to create two dfs
                    # from the same fetched data.
                    selected_index = selection.selection['rows'][0]
                    selected_id = df_vis.iloc[selected_index].name
                    render_modify_modal(supabase_client, table_name,
                                        config, selected_id, prefix)
                else:
                    st.warning('Seleziona un movimento da modificare')

        with col3:
            delete = st.button("Rimuovi Movimento", key = table_name + '_delete')
            if delete:
                if selection.selection['rows']:
                    selected_index = selection.selection['rows'][0]
                    # This line below will not work since the index of selection is relative to
                    # df_vis and not movimenti_data.
                    # selected_row = movimenti_data[selected_index]

                    # So where I need the id, I can call .name but cannot do to_dict() because I lose the index
                    # if I don't reset the index before.
                    record_id = df_vis.iloc[selected_index].name #.to_dict()

                    render_delete_modal(supabase_client, table_name, record_id)
                else:
                    st.warning('Seleziona un movimento da eliminare')


        with st.expander("Visualizza e Modifica Scadenze"):
            # Selected row.
            #
            # ATT: here I'm relying on the fact that the index, as I've already
            # verified, will be always relative to the index of the data that are
            # an input to the dataframe. In this case I am assuming that this relationship
            # holds also for movimenti_data.
            #
            # Note that reading from a view, I have names of columns that are different
            # from the prefixed names in the table.
            # Most notably I don't have prefixes.

            if selection.selection['rows']:
                selected_index = selection.selection['rows'][0]
                # If I query data from something other than df_vis, any sorting will result in
                # selecting the wrong index.
                #
                # I commented the old version for reference.
                # record_data = movimenti_data[selected_index]
                # numero_documento = record_data[prefix + 'numero']
                # data_documento   = record_data[prefix + 'data']
                # importo_totale_movimento = to_money(record_data[prefix + 'importo_totale'])
                record_data = df_vis.iloc[selected_index].to_dict()
                numero_documento = record_data['Numero']
                data_documento   = record_data['Data']
                importo_totale_movimento = to_money(record_data['Importo Totale'])

                # For now it is impossible to have anomalies in altri movimenti.
                # if numero_documento in anomalies:
                #     st.warning(anomalies.get(numero_documento))


                movement_key = {
                    rate_prefix + 'numero': numero_documento,
                    rate_prefix + 'data': data_documento
                }

                # I update the terms when: there are no terms (first page load), I've selected another term,
                # I've saved and updated the terms.
                # if st.session_state[terms_key] is None or st.session_state[selection_key] != selection \
                #         or st.session_state[are_terms_updated] == True:
                if st.session_state[terms_key] is None or st.session_state[selection_key] != numero_documento \
                        or st.session_state[are_terms_updated] == True or st.session_state.force_update == True:
                    try:
                        result = supabase_client.table('rate_' + table_name).select('*').eq('user_id', user_id) \
                            .eq(rate_prefix + 'numero', numero_documento) \
                            .eq(rate_prefix + 'data', data_documento).execute()

                        existing_terms = []
                        for row in result.data:
                            term = {
                                'id' : row['id'],
                                rate_prefix + 'data_scadenza': datetime.strptime(row[rate_prefix + 'data_scadenza'], '%Y-%m-%d').date(),
                                rate_prefix + 'data_pagamento': datetime.strptime(row[rate_prefix + 'data_pagamento'], '%Y-%m-%d').date() if row[rate_prefix + 'data_pagamento'] else None,
                                rate_prefix + 'importo_pagamento': float(row[rate_prefix + 'importo_pagamento']),
                                rate_prefix + 'display_cassa': row[rate_prefix + 'display_cassa'] or '',
                                rate_prefix + 'fattura_attesa': row[rate_prefix + 'fattura_attesa'] or '',
                                rate_prefix + 'notes': row[rate_prefix + 'notes'] or '',
                            }
                            existing_terms.append(term)
                        st.session_state[terms_key] = existing_terms
                        st.session_state[selection_key] = numero_documento
                        st.session_state[are_terms_updated] = False
                        st.session_state.force_update = False

                    # This try should be triggered only on the first loading or when I change selection
                        # so it should be safe to reset the existing terms here.
                        st.session_state[backup_terms_key] = existing_terms
                    except Exception as e:
                        #
                        #
                        #
                        #
                        # TODO; NOTE THAT I LOOSE ALMOsT ALL ERROR MSG EVEN WITH e! or str(e)
                        #
                        #
                        #
                        #
                        st.error(f"Errore nel caricamento dei termini: {str(e)}")

                # st.write(st.session_state[terms_key])
                terms_df = pd.DataFrame(st.session_state[terms_key])
                terms_df = terms_df.rename(columns = {'id':rate_prefix + 'id'})
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


                required_columns = ['Data Scadenza', 'Importo Pagamento']
                column_config = get_standard_column_config(money_columns = money_columns,
                                                           date_columns = date_columns,
                                                           required_columns = required_columns,
                                                           )

                options = fetch_all_records_from_view(supabase_client, 'casse_options')
                cleaned_options = [str(d.get('cassa')).strip() for d in options if d.get('cassa') is not None]

                # Check for any mismatches
                # if 'Display Cassa' in terms_df.columns:
                #     unique_values = [str(x).strip() for x in terms_df['Display Cassa'].dropna().unique()]
                #     mismatches = [val for val in unique_values if val not in cleaned_options and val != 'nan']
                #     if mismatches:
                #         st.warning(f"Found {len(mismatches)} values in 'Display Cassa' that don't match any option:")
                #         st.write("\nAvailable options from database:")
                #         st.write(cleaned_options)
                #         st.write('terms values')
                #         st.write(unique_values)
                
                column_config['Display Cassa'] = st.column_config.SelectboxColumn(
                    "Cassa",
                    options=cleaned_options)

                column_config['Id'] = st.column_config.TextColumn("Id")

                column_config['Notes'] = st.column_config.TextColumn("Note")

                column_config['Fattura Attesa'] = st.column_config.SelectboxColumn(
                    'Fattura Attesa',
                    options=['Nessuna','In Attesa','Ricevuta'])

                terms_df = terms_df.sort_values(by=['Data Scadenza'])

                terms_df.style.format({
                    'Importo Pagamento': format_italian_currency,
                })

                # editing_enabled = st.toggle('Modifica Tabella', key = table_name + '_toggle')

                column_order = ['Data Scadenza', 'Data Pagamento', 'Importo Pagamento', 'Display Cassa', 'Fattura Attesa', 'Notes']
                # st.write(terms_df.index)

                edited =  st.data_editor(terms_df,
                                          key=table_name + '_terms_df',
                                          column_config=column_config,
                                          hide_index=True,
                                          num_rows='dynamic',
                                          column_order = column_order,
                                          disabled=["Id"]
                                         )


                c1, c2, c3 = st.columns([3,3,1], vertical_alignment='top')

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
                            _edited = _edited.reset_index()

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
                    with st.popover("Salva o Annulla"):
                        save = st.button("Salva  ", type='primary', key = table_name + '_save_terms', use_container_width=True)
                        cancel = st.button('Annulla', key = table_name + '_cancel_terms', use_container_width=True)

                if save:
                    save_movement_terms(edited, terms_key, rate_prefix, importo_totale_movimento,
                                        config, movement_key, supabase_client, table_name,
                                        backup_terms_key, are_terms_updated)
                if cancel:
                    # NOTE IMPORTANT: for some reason, if I do
                    # st.session_state[terms_key] = st.session_state[backup_terms_key],
                    # the rerun() does not trigger the recomputing of the terms_df.
                    # I have to use a variable like undo_terms!
                    undo_terms = st.session_state[backup_terms_key]
                    st.session_state[terms_key] = undo_terms
                    st.rerun()

            else:
                st.warning('Seleziona un movimento per gestirne le rate')