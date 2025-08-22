import logging
import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from decimal import Decimal, getcontext, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta
from invoice_utils import render_field_widget, render_selectable_dataframe
from utils import extract_prefixed_field_names

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
        logging.exception(f"Database error in fetch_all_records - table: {table_name}, user_id: {user_id}")
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

        cols = st.columns(2)
        for i, (field_name, field_config) in enumerate(config_items):
            with cols[i % 2]:
                if field_name in sql_table_fields_names:
                    form_data[field_name] = render_field_widget(
                        field_name, field_config, key_suffix=f"add_{table_name}"
                    )

        col1, col2 = st.columns([1, 1])

        with col1:
            submitted = st.form_submit_button("Salva", type="primary", use_container_width=True)

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
                            data_documento_date = datetime.fromisoformat(processed_data['ma_data'])
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
                            elif table_name != 'movimenti_passivi':
                                term['rmp_numero'] = processed_data['mp_numero']
                                term['rmp_data'] = processed_data['mp_data']
                                term['rmp_importo_pagamento'] = processed_data['mp_importo_totale']
                                term['rmp_data_scadenza'] = terms_due_date
                            else:
                                raise Exception("Uniche tabelle supportate: movimenti_attivi, movimenti_passivi.")

                            # TODO; I have two insert_record_fixed functions in the db!
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
    #
    # if data_df.empty or record_id not in data_df['id'].values:
    #     st.error("Record non trovato")
    #     return

    # st.warning(f"Selezionate {len(record_ids)} fatture. Sei sicuro di voler eliminare questa fattura? L'operazione non può essere annullata.")

    # # Show record details
    # with st.expander("Visualizza dettagli fattura"):
    #     for id in record_ids:
    #
    #         field_label = get_field_label(fields_config, field_name)
    #         field_value = record.get(field_name, "")
    #
    #         # Format value based on type
    #         field_type = fields_config.get(field_name, {}).get('data_type', 'string')
    #         if field_type == 'money' and field_value:
    #             field_value = f"€ {float(field_value):,.2f}"
    #         elif field_type == 'date' and field_value:
    #             if isinstance(field_value, (date, datetime)):
    #                 field_value = field_value.strftime('%d/%m/%Y')
    #         elif field_type == 'boolean':
    #             field_value = "Sì" if field_value else "No"
    #
    #         st.write(f"**{field_label}:** {field_value}")

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Conferma Eliminazione", type="primary", use_container_width=True):
            try:

                with st.spinner("Eliminazione in corso..."):
                    # todo: check this.
                    # Supabase delete always returns empty data, so we check for no exception
                    result = supabase_client.table(table_name).delete().eq('id', record_id).execute()
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
    # TODO; in this I pass directly the record data, instead of starting from
    #  a dataframe and converting back to dictionary. Maybe I can simplify the other version.

    record_id = record_data['id']
    with st.form(f"modify_{table_name}_form"):
        # form_data will hold the updated value of the form when I click on the
        # Aggiorna button. This is because, for some reason, the code below will rerun
        # and update form_data.
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
            submitted = st.form_submit_button("💾 Aggiorna", type="primary", use_container_width=True)

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
                        result = supabase_client.table(table_name).update(processed_data).eq('id', record_id).execute()
                        if result:
                            st.success("Fattura salvata con successo nel database!")
                            time.sleep(2)
                            st.rerun()
            except Exception as e:
                print(f'Error updating invoice: {e}')
                raise

def render_terms_form(supabase_client, user_id,
                      table_name, prefix,
                      rate_prefix,
                      record_data):

    PAYMENT_METHODS = ['Bonifico', 'Contanti', 'Assegno', 'Carta di credito', 'RID', 'Altro']
    CASH_ACCOUNTS = ['Banca Intesa', 'Cassa Contanti', 'Cassa Generica', 'INTESA SAN PAOLO']

    # Because record_data, being part of the session_state, can be None
    if record_data is None:
        return

    # This is a safety measure in case, when I switch between
    # different tabs, it might happen that a record from a different
    # table is still present in the session state, thus causing errors.
    for k,v in record_data.items():
        if 'numero' in k:
            random_key = k
            break
    current_record_data_prefix = random_key[:len(prefix)]
    if current_record_data_prefix != prefix:
        return

    data_movimento              = record_data[prefix + 'data']
    importo_totale_movimento    = record_data[prefix + 'importo_totale']

    # Invoice key for database operations
    invoice_key = {
        'numero': record_data[prefix + 'numero'],
        'data': record_data[prefix + 'data']
    }

    # Load existing terms from database
    try:
        result = supabase_client.table('rate_' + table_name).select('*').eq('user_id', user_id) \
            .eq(rate_prefix + 'numero', invoice_key['numero']) \
            .eq(rate_prefix + 'data', invoice_key['data']).execute()

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

    except Exception as e:
        st.error(f"Errore nel caricamento: {str(e)}")
        existing_terms = []

    if 'edit_movimenti_attivi_terms' not in st.session_state:
        st.session_state.edit_movimenti_attivi_terms = False

    if 'current_movimenti_attivi_terms' not in st.session_state:
        if existing_terms:
            st.session_state.current_movimenti_attivi_terms = existing_terms.copy()
        else:
            st.session_state.current_movimenti_attivi_terms = [{
                rate_prefix + 'data_scadenza': datetime.strptime(data_movimento, '%Y-%m-%d').date() + timedelta(days=30),
                rate_prefix + 'data_pagamento': None,
                rate_prefix + 'importo_pagamento': importo_totale_movimento,
                rate_prefix + 'nome_cassa': '',
                rate_prefix + 'notes': None
            }]

    total_configured = sum(term[rate_prefix + 'importo_pagamento'] for term in existing_terms)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Importo Totale", f"€ {importo_totale_movimento:,.2f}")
    with col2:
        st.metric("Configurato", f"€ {total_configured:,.2f}")

    # Display existing terms in a table
    if existing_terms:
        df_display = pd.DataFrame([
            {
                'Scadenza': term[rate_prefix + 'data_scadenza'].strftime('%d/%m/%Y'),
                'Importo': f"€ {term[rate_prefix + 'importo_pagamento']:,.2f}",
                'Cassa': term[rate_prefix + 'nome_cassa'],
                'Note': term[rate_prefix + 'notes'],
                'Pagato': '✅' if term[rate_prefix + 'data_pagamento'] else '❌',
                'Data Pagamento': term[rate_prefix + 'data_pagamento'].strftime('%d/%m/%Y') if term[rate_prefix + 'data_pagamento'] else '-'
            }
            for term in existing_terms
        ])
        st.dataframe(df_display, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Aggiungi o Modifica Movimento", type="primary", use_container_width=True):
            st.session_state.edit_movimenti_attivi_terms = True
            # CRITICAL: Reset current terms to existing data when entering edit mode
            st.session_state.current_movimenti_attivi_terms = existing_terms.copy() if existing_terms else [{
                rate_prefix + 'data_scadenza': datetime.strptime(data_movimento, '%Y-%m-%d').date() + timedelta(days=30),
                rate_prefix + 'data_pagamento': None,
                rate_prefix + 'importo_pagamento': importo_totale_movimento,
                rate_prefix + 'nome_cassa': '',
                rate_prefix + 'notes': None
            }]
            st.rerun()

    if st.session_state.edit_movimenti_attivi_terms:

        with st.expander("Configurazione Rapida", expanded=True):
            split_col1, split_col2, split_col3 = st.columns([2, 2, 1])

            with split_col1:
                num_installments = st.number_input("Numero rate", min_value=1, max_value=12, value=1)

            with split_col2:
                interval_days = st.number_input("Giorni tra rate", min_value=1, max_value=365, value=30, step=15)

            with split_col3:
                if st.button("Applica Configurazione", use_container_width=True):
                    st.session_state.current_movimenti_attivi_terms = auto_split_payment_movimenti(
                        importo_totale_movimento, num_installments,
                        data_movimento, rate_prefix, interval_days)
                    st.rerun()

        for i, term in enumerate(st.session_state.current_movimenti_attivi_terms):
            with st.container():
                st.markdown(f"##### Scadenza {i + 1}")

                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

                with col1:
                    new_date = st.date_input(
                        "Data Scadenza",
                        value=term[rate_prefix + 'data_scadenza'],
                        key=f"date_{i}"
                    )
                    st.session_state.current_movimenti_attivi_terms[i][rate_prefix + 'data_scadenza'] = new_date

                with col2:
                    new_amount = st.number_input(
                        "Importo (€)",
                        min_value=0.0,
                        value=max(0.0, term[rate_prefix + 'importo_pagamento']),
                        step=0.01,
                        key=f"amount_{i}"
                    )
                    st.session_state.current_movimenti_attivi_terms[i][rate_prefix + 'importo_pagamento'] = new_amount

                with col3:
                    new_cassa = st.selectbox(
                        "Cassa",
                        CASH_ACCOUNTS,
                        index=CASH_ACCOUNTS.index(term[rate_prefix + 'nome_cassa']) if term[rate_prefix + 'nome_cassa'] in CASH_ACCOUNTS else 0,
                        key=f"cassa_{i}"
                    )
                    st.session_state.current_movimenti_attivi_terms[i][rate_prefix + 'nome_cassa'] = new_cassa

                with col4:
                    st.write("")  # Spacing
                    st.write("")  # Spacing
                    if len(st.session_state.current_movimenti_attivi_terms) > 1:
                        if st.button("🗑️", key=f"remove_{i}", help="Rimuovi scadenza"):
                            st.session_state.current_movimenti_attivi_terms.pop(i)
                            st.rerun()

                # Second row for additional details
                col1, col2, col3 = st.columns([2, 2, 2])

                with col1:
                    new_notes = st.text_input(
                        "Note (opzionale)",
                        value=term.get(rate_prefix + 'notes', '') or '',
                        key=f"notes_{i}"
                    )
                    st.session_state.current_movimenti_attivi_terms[i][rate_prefix + 'notes'] = new_notes

                with col2:
                    payment_date = st.date_input(
                        "Data Pagamento (se pagato)",
                        value=term[rate_prefix + 'data_pagamento'],
                        key=f"payment_date_{i}",
                        help="Lascia vuoto se non ancora pagato"
                    )
                    st.session_state.current_movimenti_attivi_terms[i][rate_prefix + 'data_pagamento'] = payment_date

                st.markdown("---")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Aggiungi Scadenza", use_container_width=True):
                new_term = {
                    rate_prefix + 'data_scadenza': datetime.strptime(data_movimento, '%Y-%m-%d').date() + timedelta(days=30),
                    rate_prefix + 'importo_pagamento': 0.0,
                    rate_prefix + 'nome_cassa': '',
                    rate_prefix + 'notes': '',
                    rate_prefix + 'data_pagamento': None
                }
                st.session_state.current_movimenti_attivi_terms.append(new_term)
                st.rerun()

        with col2:
            if st.session_state.current_movimenti_attivi_terms:
                if st.button("Dividi Importo tra scadenze", use_container_width=True):
                    if len(st.session_state.current_movimenti_attivi_terms) > 0:
                        # Keep existing payment dates but recalculate amounts
                        payment_dates = [term[rate_prefix + 'data_pagamento'] for term in st.session_state.current_movimenti_attivi_terms]
                        payment_expected_dates = [term[rate_prefix + 'data_scadenza'] for term in st.session_state.current_movimenti_attivi_terms]
                        st.session_state.current_movimenti_attivi_terms = auto_split_payment_movimenti(
                            importo_totale_movimento,
                            len(st.session_state.current_movimenti_attivi_terms),
                            data_movimento,
                            rate_prefix
                        )
                        # Restore payment dates
                        for i, payment_date in enumerate(payment_dates):
                            if i < len(st.session_state.current_movimenti_attivi_terms):
                                st.session_state.current_movimenti_attivi_terms[i][rate_prefix + 'data_pagamento'] = payment_date
                        for i, payment_date in enumerate(payment_expected_dates):
                            if i < len(st.session_state.current_movimenti_attivi_terms):
                                st.session_state.current_movimenti_attivi_terms[i][rate_prefix + 'data_scadenza'] = payment_date
                        st.rerun()

        # Save buttons
        if st.session_state.current_movimenti_attivi_terms:
            st.markdown("---")
            col1, col2 = st.columns(2)

            with col1:
                if st.button("💾 Salva Scadenze", type="primary", use_container_width=True):
                    is_valid, errors = validate_payment_terms(st.session_state.current_movimenti_attivi_terms,
                                                              importo_totale_movimento,
                                                              rate_prefix)

                    if not is_valid:
                        for error in errors:
                            st.error(error)
                    else:
                        success = False
                        try:
                            # Transaction: delete existing and insert new
                            supabase_client.table('rate_' + table_name).delete().eq('user_id', user_id) \
                                .eq(rate_prefix + 'numero', invoice_key['numero']) \
                                .eq(rate_prefix + 'data', invoice_key['data']).execute()

                            # Insert new payment terms
                            for term in st.session_state.current_movimenti_attivi_terms:
                                term_data = {
                                    'user_id': user_id,
                                    rate_prefix + 'numero': invoice_key['numero'],
                                    rate_prefix + 'data': invoice_key['data'],
                                    rate_prefix + 'data_scadenza': term[rate_prefix + 'data_scadenza'].strftime('%Y-%m-%d'),
                                    rate_prefix + 'importo_pagamento': term[rate_prefix + 'importo_pagamento'],
                                    rate_prefix + 'nome_cassa': term[rate_prefix + 'nome_cassa'],
                                    rate_prefix + 'notes': term[rate_prefix + 'notes'],
                                    rate_prefix + 'data_pagamento': term[rate_prefix + 'data_pagamento'].strftime('%Y-%m-%d') if term[rate_prefix + 'data_pagamento'] else None
                                }
                                supabase_client.table('rate_' + table_name).insert(term_data).execute()
                            success = True
                        except Exception as e:
                            st.error(f"Errore nel salvataggio: {str(e)}")

                        if success:
                            st.success(f"✅ Scadenze salvate con successo!")
                            # Clear edit mode and temp data
                            st.session_state.edit_movimenti_attivi_terms = False
                            if 'current_movimenti_attivi_terms' in st.session_state:
                                del st.session_state.current_movimenti_attivi_terms
                            st.rerun()

            with col2:
                if st.button("❌ Annulla", use_container_width=True):
                    st.session_state.edit_movimenti_attivi_terms = False
                    if 'current_movimenti_attivi_terms' in st.session_state:
                        del st.session_state.current_movimenti_attivi_terms
                    st.rerun()

    # Return early if not in edit mode
    return

def render_movimenti_crud_page(supabase_client, user_id,
                     table_name, prefix,
                     rate_prefix,
                     config):
    # Initialize session state for managing which view to show.
    # List is the main page, where I can open the modal to
    # add, modify and delete.
    # Terms is the new page for terms.
    if 'current_view' not in st.session_state:
        st.session_state.current_view = 'list'  # 'list' or 'terms'
    if 'selected_movement' not in st.session_state:
        st.session_state.selected_movement = None


    result_data = fetch_all_records(supabase_client, table_name, user_id)
    if not result_data:
        st.warning("Nessun movimento trovato. Creare un movimento prima di proseguire.")
        add = st.button("Aggiungi Movimento", type='primary', key = table_name + 'add_no_movements')
        if add:
            render_add_modal(supabase_client, table_name, config, prefix)
        return

    # Show terms management view if active
    if st.session_state.current_view == 'terms' and st.session_state.selected_movement:

        if st.button("← Torna indietro", type="secondary", key = table_name + 'back'):
            st.session_state.current_view = 'list'
            st.session_state.selected_movement = None
            # Clear any edit state when going back
            if 'edit_movimenti_attivi_terms' in st.session_state:
                del st.session_state.edit_movimenti_attivi_terms
            if 'current_movimenti_attivi_terms' in st.session_state:
                del st.session_state.current_movimenti_attivi_terms
            st.rerun()

        # Render the terms form - this will now persist properly
        render_terms_form(supabase_client, user_id, table_name, prefix, rate_prefix, st.session_state.selected_movement)

    else:
        # Ensure we're in list view
        st.session_state.current_view = 'list'

        selection = render_selectable_dataframe(result_data, 'single-row', 'rerun')

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            add = st.button("Aggiungi Movimento", type='primary', use_container_width=True
                           , key = table_name + 'add')
            if add:
                render_add_modal(supabase_client, table_name, config, prefix)

        with col2:
            modify = st.button("Modifica Movimento", use_container_width=True, key = table_name + 'modify')
            if modify:
                if selection.selection['rows']:
                    selected_index = selection.selection['rows'][0]
                    selected_row = result_data[selected_index]
                    render_modify_modal(supabase_client, table_name,
                                        config, selected_row, prefix)
                else:
                    st.warning('Seleziona un movimento da modificare')

        with col3:
            delete = st.button("Rimuovi Movimento", use_container_width=True, key = table_name + 'delete')
            if delete:
                if selection.selection['rows']:
                    selected_index = selection.selection['rows'][0]
                    selected_id = result_data[selected_index]['id']
                    render_delete_modal(supabase_client, table_name, selected_id)
                else:
                    st.warning('Seleziona un movimento da eliminare')

        with col4:
            manage_terms = st.button("Gestisci Scadenze", use_container_width=True, key = table_name + 'manage')
            if manage_terms:
                if selection.selection['rows']:
                    selected_index = selection.selection['rows'][0]
                    selected_row = result_data[selected_index]

                    st.session_state.current_view = 'terms'
                    st.session_state.selected_movement = selected_row

                    # Clear any existing edit state to start fresh
                    if 'edit_movimenti_attivi_terms' in st.session_state:
                        del st.session_state.edit_movimenti_attivi_terms
                    if 'current_movimenti_attivi_terms' in st.session_state:
                        del st.session_state.current_movimenti_attivi_terms

                    st.rerun()
                else:
                    st.warning('Seleziona un movimento di cui modificare le rate')