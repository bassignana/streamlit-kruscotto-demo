from decimal import Decimal, ROUND_HALF_UP
import plotly.graph_objects as go
from datetime import datetime, timedelta
import streamlit as st
from dateutil.relativedelta import relativedelta
from invoice_xml_mapping import XML_FIELD_MAPPING
from config import technical_fields, uppercase_prefixes
from utils import setup_page, money_to_string, to_money, fetch_all_records_from_view, extract_prefixed_field_names, \
    render_field_widget, are_all_required_fields_present, remove_prefix, extract_field_names, fetch_record_from_id, \
    fetch_all_records, get_standard_column_config, format_italian_currency, get_df_metric
import pandas as pd

def create_monthly_invoices_summary_chart(data_dict, show_amounts=False):

    # Extract months and values
    months = list(data_dict.keys())
    fatture_emesse = []
    fatture_ricevute = []

    # Use Decimal for precise financial calculations
    for month in months:
        attivi = Decimal(str(data_dict[month]['Fatture Emesse']))
        passivi = Decimal(str(data_dict[month]['Fatture Ricevute']))

        # Round to 2 decimal places using banker's rounding
        attivi_rounded = float(attivi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        passivi_rounded = float(passivi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

        fatture_emesse.append(attivi_rounded)
        fatture_ricevute.append(passivi_rounded)

    # Create the figure
    fig = go.Figure()

    # Add Fatture Emesse (Active Movements) - Green bars
    fig.add_trace(go.Bar(
        name='Fatture Emesse',
        x=months,
        y=fatture_emesse,
        marker_color='#16a34a',  # Green color
        opacity=0.85,
        text=[f'€ {val:,.2f}' if val != 0 else '' for val in fatture_emesse] if show_amounts else None,
        textposition='outside' if show_amounts else None,
        textfont=dict(size=10, color='#16a34a') if show_amounts else None,
        hovertemplate='<b>%{fullData.name}</b><br>' +
                      'Mese: %{x}<br>' +
                      'Importo: € %{y:,.2f}<extra></extra>'
    ))

    # Add Fatture Ricevute (Passive Movements) - Red bars
    fig.add_trace(go.Bar(
        name='Fatture Ricevute',
        x=months,
        y=fatture_ricevute,
        marker_color='#dc2626',  # Red color
        opacity=0.85,
        text=[f'€ {val:,.2f}' if val != 0 else '' for val in fatture_ricevute] if show_amounts else None,
        textposition='outside' if show_amounts else None,
        textfont=dict(size=10, color='#dc2626') if show_amounts else None,
        hovertemplate='<b>%{fullData.name}</b><br>' +
                      'Mese: %{x}<br>' +
                      'Importo: € %{y:,.2f}<extra></extra>'
    ))

    # Update layout
    fig.update_layout(
        title={
            'text': 'Fatture Mensili',
            'font': {'size': 16, 'color': '#1f2937'},
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='Mesi',
        yaxis_title='Importo (€)',
        barmode='group',  # Groups bars side by side
        height=500,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=12)
        ),
        plot_bgcolor='white',  # White background
        paper_bgcolor='white',  # White background
        xaxis=dict(
            showgrid=False,  # Remove grid
            showline=True,
            linewidth=1,
            linecolor='rgba(128,128,128,0.3)'
        ),
        yaxis=dict(
            showgrid=False,  # Remove grid
            showline=True,
            linewidth=1,
            linecolor='rgba(128,128,128,0.3)',
            tickformat=',.0f'
        ),
        margin=dict(t=80, b=40, l=60, r=40)
    )

    # Disable zoom and pan interactions
    fig.update_layout(
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True)
    )

    return fig

def auto_split_payment_invoice(importo_totale_documento: Decimal, num_installments, start_date,
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

            rate_prefix + 'data_scadenza_pagamento':  datetime.strptime(start_date, '%Y-%m-%d').date() + timedelta(days=interval_days * (i + 1)),
            rate_prefix + 'importo_pagamento_rata': installment_amount,
            rate_prefix + 'nome_cassa': '',
            rate_prefix + 'notes': f'Rata {i + 1} di {num_installments}',
            rate_prefix + 'data_pagamento_rata': None  # Not paid yet
        }
        terms.append(term)

    return terms

def save_invoice_terms(edited, terms_key, rate_prefix, importo_totale_movimento,
                       config, invoice_key, supabase_client, table_name,
                       backup_terms_key, document_not_nullable_fields, are_terms_updated):
    if len(edited) == 0:
        st.warning('Impossibile salvare una fattura senza scadenze di pagamento. '
                   'Inserire delle nuove scadenze o cliccare su Annulla per scartare '
                   'tutte le modifiche apportate')
    else:
        try:

            _edited = edited.copy()
            _edited.columns = [rate_prefix + col.replace(' ','_').lower() for col in _edited.columns]
            up_to_date_terms = []
            for k,v in _edited.T.to_dict().items():
                up_to_date_terms.append(v)
            terms = up_to_date_terms

            # Verify total configured
            # TODO; This does not work at first try
            total_configured = to_money(0)
            for term in terms:
                total_configured += to_money(term[rate_prefix + 'importo_pagamento_rata'])
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

            # Adding invoices keys, if missing, for insert.
            for term in terms_to_save:
                for k,v in invoice_key.items():
                    if k not in term:
                        term[k] = v

            # Adding ather not nullable fields, if missing, for insert.
            for term in terms_to_save:
                for k,v in document_not_nullable_fields.items():
                    if k not in term:
                        term[k] = v

            # Verify that all required field are present
            sql_table_fields_names = extract_prefixed_field_names(
                'sql/02_create_tables.sql',
                rate_prefix)

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

            result = supabase_client.rpc('upsert_terms', {
                'table_name': 'rate_' + table_name,
                'delete_key': invoice_key,
                'terms': terms_to_save
            }).execute()

            if result.data.get('success', False):
                st.success("Modifiche eseguite con successo")

                # I've tested it quicly, it seems to work.
                st.session_state[backup_terms_key] = terms
                st.session_state[are_terms_updated] = True
                st.rerun()
            else:
                st.error(f'Errore nel salvataggio: {result}')

        # todo: fix error management / logging.
        #  Here is interesting because the above catches db error that are not
        #  exceptions, the below only exceptions.
        except Exception as e:
            st.error(f"Eccezione nel salvataggio: {str(e)}")

@st.dialog("Aggiungi fattura")
def render_invoice_add_modal(supabase_client, table_name, fields_config, prefix):

    with st.form(f"add_{table_name}_form",
                 clear_on_submit=False,
                 enter_to_submit=False):

        form_data = {}
        result = supabase_client.table('user_data').select('ud_partita_iva') \
            .eq('user_id', st.session_state.user.id).execute()

        has_errored = (hasattr(result, 'error') and result.error)

        # Todo: check for len == 1
        if has_errored:
            st.error(f"Errore nella lettura della P.IVA aziendale: {result.error.message}")
            return
        else:
            piva = result.data[0].get('ud_partita_iva', False)
            if not piva:
                st.error(f"Errore nell'estrazione della P.IVA aziendale.")
                return

        config_items = list(fields_config.items())
        # Here is one of the differences with movimenti, the names in the config are
        # unprefixed.
        sql_table_fields_names = extract_field_names('sql/02_create_tables.sql', prefix)

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
                    #
                    #
                    #
                    #
                    #
                    #
                    # TODO: test that I don't need to specify a separate branch for each table.
                    # No! se emetto fattura, io sono il prestatore e deve essere bloccata ma
                    # se si tratta di una fattura ricevuta, il prestatore e' l'altro, quindi non deve essere bloccato?
                    #
                    #
                    #
                    #
                    #
                    #
                    if field_name == 'partita_iva_prestatore' and table_name == 'fatture_emesse':
                        form_data[field_name] = render_field_widget(
                            field_name, field_config,
                            piva, f"add_{table_name}", True)
                    else:
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

                    prefixed_processed_data = {}
                    for k,v in processed_data.items():
                        prefixed_processed_data[prefix + k] = v

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
                            data_documento_date = datetime.fromisoformat(prefixed_processed_data[prefix + 'data_documento'])
                            first_day = datetime(data_documento_date.year, data_documento_date.month, 1)
                            last_day_next_X_months = first_day + relativedelta(months=MONTHS_IN_ADVANCE, days=-1)
                            # terms_due_date = [last_day_next_X_months.date().isoformat()]
                            terms_due_date = last_day_next_X_months.date().isoformat() # Not a list!

                            term = {}
                            if table_name == 'fatture_emesse':
                                term['rfe_numero_fattura'] = prefixed_processed_data['fe_numero_fattura']
                                term['rfe_data_documento'] = prefixed_processed_data['fe_data_documento']
                                term['rfe_importo_pagamento_rata'] = prefixed_processed_data['fe_importo_totale_documento']
                                term['rfe_data_scadenza_pagamento'] = terms_due_date
                                term['rfe_partita_iva_prestatore'] = prefixed_processed_data['fe_partita_iva_prestatore']
                            elif table_name == 'fatture_ricevute':
                                term['rfr_numero_fattura'] = prefixed_processed_data['fr_numero_fattura']
                                term['rfr_data_documento'] = prefixed_processed_data['fr_data_documento']
                                term['rfr_importo_pagamento_rata'] = prefixed_processed_data['fr_importo_totale_documento']
                                term['rfr_data_scadenza_pagamento'] = terms_due_date
                                term['rfr_partita_iva_prestatore'] = prefixed_processed_data['fr_partita_iva_prestatore']
                            else:
                                raise Exception("Uniche tabelle supportate: fatture_emesse, fatture_ricevute.")

                            result = supabase_client.rpc('insert_record', {
                                'table_name': table_name,
                                'record_data': prefixed_processed_data,
                                'terms_table_name': 'rate_' + table_name,
                                'terms_data': [term],
                                'test_user_id': None
                            }).execute()



                            has_errored = (hasattr(result, 'error') and result.error)

                            if has_errored:
                                st.error(f"Errore nell'inserimento manuale della fattura: {result.error.message}")
                                return
                            else:
                                st.success("Fattura salvata con successo")
                                st.rerun()
                        # This exception handling does not show the message to the ui, neither raise
                        # nothing. It is completely invisible.
                        except Exception as e:
                            st.error("Error inserting invoice data:", e)
                            raise

            except Exception as e:
                print(f'Error adding invoice manually: {e}')

@st.dialog("Modifica fattura")
def render_invoice_modify_modal(supabase_client, table_name, fields_config, selected_id, prefix):

    selected_row_parent_data = fetch_record_from_id(supabase_client, table_name, selected_id)

    with st.form(f"modify_{table_name}_form",
                 clear_on_submit=False,
                 enter_to_submit=False):
        form_data = {}

        config_items = list(fields_config.items())
        sql_table_fields_names = extract_field_names('sql/02_create_tables.sql', prefix)

        cols = st.columns(2)
        column_flag = False  # Start with left column (index 0)
        for i, (field_name, field_config) in enumerate(config_items):
            with cols[int(column_flag)]:
                if field_name in sql_table_fields_names:
                    record_value = selected_row_parent_data.get(prefix + field_name, None)
                    if field_name == 'partita_iva_prestatore' and table_name == 'fatture_emesse':
                        form_data[field_name] = render_field_widget(
                            field_name, field_config,
                            record_value, f"add_{table_name}", True)
                    else:
                        form_data[field_name] = render_field_widget(
                            field_name, field_config, record_value,
                            f"add_{table_name}", False
                        )
                    # Only invert the flag after actually rendering a field
                    column_flag = not column_flag

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

                    # From the code above, we know that form_data will hold either a value or None,
                    # and we know that if we pass None, the supabase API will convert to NONE or
                    # default value.
                    for name, value in form_data.items():
                        # All string otherwise 'Object of type date is not JSON serializable'
                        processed_data[name] = str(value)

                    prefixed_processed_data = {}
                    for k,v in processed_data.items():
                        prefixed_processed_data[prefix + k] = v

                    prefixed_processed_data['user_id'] = st.session_state.user.id

                    with st.spinner("Salvataggio in corso..."):
                        # The addition of .eq() with user_id, is for consistency and safety.
                        # It should not be necessary since ids are unique in the table.
                        result = supabase_client.table(table_name).update(prefixed_processed_data) \
                            .eq('user_id', st.session_state.user.id) \
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

@st.dialog("Rimuovi fattura")
def render_invoice_delete_modal(supabase_client, table_name, selected_row, rate_prefix, prefix):

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Conferma Eliminazione", type="primary",
                     key = table_name + '_delete_modal_button'):
            try:
                with st.spinner("Eliminazione in corso..."):
                    record_id = selected_row['id']

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

def render_invoice_crud_page(supabase_client, user_id,
                               table_name, prefix,
                               rate_prefix,
                               config):
    """
    For comments, see movimenti_crud_page,
    but the main problem is that I try to interact with a view.
    If I just display the view, I can name the columns whatever I want,
    but when I need to interact with the view, or using the data as input,
    then is different.
    This is the problem with the casse situation, but also when I display a view
    for a select dataframe, and then I have to retrieve data, although in this second
    case the pattern of getting the record Id and starting from there is a step forward.
    For now, at least naming the view column with some sort of convention will help mitigate
    the bad infrastructure design.
    """
    terms_key = table_name + '_terms'
    backup_terms_key = table_name + '_backup_terms'
    selection_key = table_name + table_name + '_selected_invoice'
    are_terms_updated = table_name + '_are_terms_updated'

# Selected invoice is only used for knowing when to refetch data
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



    check_invoices = fetch_all_records(supabase_client, table_name, user_id)
    check_terms = pd.DataFrame(fetch_all_records(supabase_client, 'rate_' + table_name, user_id))
    anomalies = {}
    for invoice in check_invoices:
        number_key = invoice[prefix + 'numero_fattura']
        date_key = invoice[prefix + 'data_documento']
        i_terms = check_terms[(check_terms[rate_prefix + 'numero_fattura'] == number_key) & \
                              (check_terms[rate_prefix + 'data_documento'] == date_key)]
        total_i = to_money(invoice[prefix + 'importo_totale_documento'])
        total_i_terms = to_money(i_terms[rate_prefix + 'importo_pagamento_rata'].sum())
        if total_i != total_i_terms:
            anomalies[number_key] = (f'ANOMALIA: La fattura ha un importo '
                                     f'totale di {total_i} Euro, mentre le relative scadenze hanno un importo '
                                     f'totale di {total_i_terms} Euro. Assicurarsi di far combaciare gli importi')

    invoices_data = fetch_all_records_from_view(supabase_client, table_name + '_overview')

    if not invoices_data:
        st.warning("Nessuna fattura trovata. Caricare o creare una fattura prima di proseguire.")
        add = st.button("Aggiungi Fattura", type='primary', key = table_name + '_add_first_invoice')
        if add:
            render_invoice_add_modal(supabase_client, table_name,
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
        df_vis = pd.DataFrame(invoices_data)
        df_vis = df_vis.set_index('id')
        df_vis.columns = [
            col.replace('_', ' ').title() if isinstance(col, str) else str(col)
            for col in df_vis.columns
        ]

        for tech_field in technical_fields:
            if tech_field in df_vis.columns:
                df_vis = df_vis.drop([tech_field], axis = 1)
        df_vis.columns = [remove_prefix(col, uppercase_prefixes) for col in df_vis.columns]

        df_vis['Anomalie'] = df_vis['Numero Fattura'].apply(lambda x: 'Scadenze Incongruenti' if x in anomalies else 'No')

        if table_name == 'fatture_emesse':
            money_columns = ['Importo Totale Documento', 'Incassato', 'Saldo']
        elif table_name == 'fatture_ricevute':
            money_columns = ['Importo Totale Documento', 'Pagato', 'Saldo']
        else:
            raise Exception("Column identification: wrong table name?")
        column_config = {}
        for col in df_vis.columns:
            if col in money_columns:
                column_config[col] = st.column_config.NumberColumn(
                    label=col,
                    format="accounting",
                )

        df_vis = df_vis.sort_values(by = ['Data Documento', 'Numero Fattura'])

        selection = st.dataframe(df_vis, use_container_width=True,
                                 selection_mode = 'single-row',
                                 on_select='rerun',
                                 hide_index = True,
                                 key = table_name + 'selection_df',
                                 column_config=column_config)

        col1, col2, col3, space = st.columns([1,1,1,4])
        with col1:
            add = st.button("Aggiungi Fattura", type='primary', key = table_name + '_add')
            if add:
                render_invoice_add_modal(supabase_client, table_name,
                                         config,
                                         prefix)

        with col2:
            modify = st.button("Modifica Fattura", key = table_name + '_modify')
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
                    render_invoice_modify_modal(supabase_client, table_name,
                                        config, selected_id, prefix)
                else:
                    st.warning('Seleziona un movimento da modificare')

        with col3:
            delete = st.button("Rimuovi Fattura", key = table_name + '_delete')
            if delete:
                if selection.selection['rows']:
                    selected_index = selection.selection['rows'][0]
                    selected_row = invoices_data[selected_index]

                    render_invoice_delete_modal(supabase_client, table_name, selected_row, rate_prefix, prefix)
                else:
                    st.warning('Seleziona un movimento da eliminare')


        with st.expander("Visualizza e Modifica Scadenze"):

            if selection.selection['rows']:
                selected_index = selection.selection['rows'][0]
                record_data = invoices_data[selected_index]
                numero_documento = record_data[prefix + 'numero_fattura']
                data_documento   = record_data[prefix + 'data_documento']
                importo_totale_documento = to_money(record_data[prefix + 'importo_totale_documento'])

                if numero_documento in anomalies:
                    st.warning(anomalies.get(numero_documento))

                result = supabase_client.table(table_name).select(prefix + 'partita_iva_prestatore') \
                                        .eq('id', record_data['id']) \
                                        .eq('user_id', st.session_state.user.id).execute()
                piva_prestatore = result.data[0].get(prefix + 'partita_iva_prestatore', None)
                if piva_prestatore is None:
                    st.error('Errore nel reperire la P.IVA prestatore')
                    return



                document_key = {
                    rate_prefix + 'numero_fattura': numero_documento,
                    rate_prefix + 'data_documento': data_documento
                }

                document_not_nullable_fields = {
                    rate_prefix + 'partita_iva_prestatore': piva_prestatore
                }

                if st.session_state[terms_key] is None or st.session_state[selection_key] != numero_documento \
                        or st.session_state[are_terms_updated] == True:
                    try:
                        result = supabase_client.table('rate_' + table_name).select('*').eq('user_id', user_id) \
                            .eq(rate_prefix + 'numero_fattura', numero_documento) \
                            .eq(rate_prefix + 'data_documento', data_documento).execute()

                        existing_terms = []
                        for row in result.data:
                            term = {
                                rate_prefix + 'data_scadenza_pagamento': datetime.strptime(row[rate_prefix + 'data_scadenza_pagamento'], '%Y-%m-%d').date(),
                                rate_prefix + 'data_pagamento_rata': datetime.strptime(row[rate_prefix + 'data_pagamento_rata'], '%Y-%m-%d').date() if row[rate_prefix + 'data_pagamento_rata'] else None,
                                # rate_prefix + 'importo_pagamento_rata': float(row[rate_prefix + 'importo_pagamento_rata']),
                                rate_prefix + 'importo_pagamento_rata': to_money(row[rate_prefix + 'importo_pagamento_rata']),
                                rate_prefix + 'nome_cassa': row[rate_prefix + 'nome_cassa'] or '',
                                rate_prefix + 'notes': row[rate_prefix + 'notes'] or '',
                            }
                            existing_terms.append(term)
                        st.session_state[terms_key] = existing_terms
                        st.session_state[selection_key] = numero_documento
                        st.session_state[are_terms_updated] = False

                        # This try should be triggered only on the first loading or when I change selection
                        # so it should be safe to reset the existing terms here.
                        st.session_state[backup_terms_key] = existing_terms
                    except Exception as e:
                        st.error(f"Errore nel caricamento dei termini delle fatture: {str(e)}")

                terms_df = pd.DataFrame(st.session_state[terms_key])
                terms_df.columns = [col[len(rate_prefix):].replace('_',' ').title() for col in terms_df.columns]

                # Since some dates can be valued as None, ensure that the date columns
                # are correctly represented as dates.
                date_columns = ['Data Scadenza Pagamento', 'Data Pagamento Rata']
                money_columns = ['Importo Pagamento Rata']
                for col in date_columns:
                    # This is the correct way to convert a possibly Null column, interpreted
                    # as a string by pandas to a datetime.date data format while keeping None
                    # instead of NaT.
                    terms_df[col] = terms_df[col].apply(lambda x: None if x is None or pd.isna(x) else pd.to_datetime(x).date())


                required_columns = ['Data Scadenza Pagamento', 'Importo Pagamento Rata']
                column_config = get_standard_column_config(money_columns = money_columns,
                                                           date_columns = date_columns,
                                                           required_columns = required_columns,
                                                           )

                options = fetch_all_records_from_view(supabase_client, 'casse_options')
                cleaned_options = [d.get('cassa') for d in options]

                column_config['Nome Cassa'] = st.column_config.SelectboxColumn(
                    "Cassa",
                    options=cleaned_options)

                column_config['Notes'] = st.column_config.TextColumn("Note")

                terms_df = terms_df.sort_values(by=['Data Scadenza'])

                terms_df.style.format({
                    'Importo Pagamento Rata': format_italian_currency,
                })

                column_order = ['Data Scadenza Pagamento', 'Data Pagamento Rata', 'Importo Pagamento Rata', 'Nome Cassa', 'Notes']

                edited =  st.data_editor(terms_df,
                                         key=table_name + '_terms_df',
                                         column_config=column_config,
                                         hide_index=True,
                                         num_rows='dynamic',
                                         column_order = column_order)


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

                                up_to_date_terms = auto_split_payment_invoice(
                                    importo_totale_documento, num_installments, data_documento, rate_prefix, interval_days
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

                            total_decimal          = to_money(importo_totale_documento)
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
                                        up_to_date_terms[i][rate_prefix + 'importo_pagamento_rata'] = total_decimal - total_allocated
                                    else:
                                        up_to_date_terms[i][rate_prefix + 'importo_pagamento_rata'] = amount_per_installment
                                        total_allocated += amount_per_installment

                                st.session_state[terms_key] = up_to_date_terms
                                st.rerun()
                with c3:
                    with st.popover("Salva o Annulla"):
                        save = st.button("Salva  ", type='primary', key = table_name + '_save_terms', use_container_width=True)
                        cancel = st.button('Annulla', key = table_name + '_cancel_terms', use_container_width=True)

                if save:
                    save_invoice_terms(edited, terms_key, rate_prefix, importo_totale_documento,
                                        config, document_key, supabase_client, table_name, backup_terms_key,
                                       document_not_nullable_fields, are_terms_updated)
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





def main():
    user_id, supabase_client, page_can_render = setup_page("Gestione Fatture")

    if page_can_render:
        # sommario, emesse, ricevute, upload = st.tabs(["Sommario", "Fatture Emesse", "Fatture Ricevute", "Carica Fatture"])
        sommario, emesse, ricevute = st.tabs(["Sommario", "Fatture Emesse", "Fatture Ricevute"])

        with sommario:

            result = supabase_client.table('monthly_invoice_summary').select('*').execute()

            if not result.data:
                st.warning("Nessun dato disponibile per il periodo selezionato")
            else:

                df = pd.DataFrame(result.data)
                df.columns = [
                    col.replace('_', ' ').title() if isinstance(col, str) else str(col)
                    for col in df.columns
                ]
                df = df.set_index(df.columns[0])

                column_config = {}
                for col in df.columns:
                    column_config[col] = st.column_config.NumberColumn(
                            label=col,
                            format="accounting",
                            width = 60
                    )

                c1, c2 = st.columns([1,3])

                with c1:
                    emesse_total = df.loc['Fatture Emesse',:].sum()
                    ricevute_total = df.loc['Fatture Ricevute',:].sum()

                    st.subheader(' ')
                    get_df_metric('Totale Fatture Emesse (€)', emesse_total)
                    get_df_metric('Totale Fatture Ricevute (€)', ricevute_total)
                    get_df_metric('Saldo Fatture (€)', emesse_total - ricevute_total)

                with c2:
                    fig = create_monthly_invoices_summary_chart(df.to_dict(), show_amounts=False)
                    st.plotly_chart(fig)

                st.dataframe(df, use_container_width=True, column_config=column_config)

                different_year_attivi = supabase_client.table('fatture_emesse').select('*') \
                    .or_('fe_data_documento.lt.2025-01-01,fe_data_documento.gt.2025-12-31').execute()
                different_year_passivi = supabase_client.table('fatture_ricevute').select('*') \
                    .or_('fr_data_documento.lt.2025-01-01,fr_data_documento.gt.2025-12-31').execute()

                if any([different_year_attivi.data, different_year_passivi.data]):
                    with st.expander('Avvisi'):
                        st.info("""Sono caricate fatture con data diversa dall'anno 2025.
                         Nel TAB Sommario saranno mostrate solo i dati relativi all'anno corrente.""")

        with emesse:
            render_invoice_crud_page(supabase_client, user_id,
                                       'fatture_emesse', 'fe_',
                                       'rfe_',
                                       XML_FIELD_MAPPING)

        with ricevute:
            render_invoice_crud_page(supabase_client, user_id,
                                     'fatture_ricevute', 'fr_',
                                     'rfr_',
                                     XML_FIELD_MAPPING)

        # with upload:
        #     render_generic_xml_upload_section(supabase_client, user_id)












if __name__ == '__main__':
    main()
