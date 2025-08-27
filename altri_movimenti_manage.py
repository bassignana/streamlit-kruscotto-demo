import time
from decimal import getcontext, Decimal, ROUND_HALF_UP

import streamlit as st
from altri_movimenti_utils import render_movimenti_crud_page, fetch_all_records, are_all_required_fields_present, \
    render_add_modal, render_modify_modal, render_delete_modal
from utils import setup_page, create_monthly_line_chart, get_standard_column_config, extract_prefixed_field_names
from altri_movimenti_config import altri_movimenti_config
import pandas as pd
from datetime import datetime, timedelta

def to_money(amount):
    getcontext().prec = 28
    MONEY_QUANTIZE    = Decimal('0.01')  # 2 decimal places
    CURRENCY_ROUNDING = ROUND_HALF_UP

    if amount is None:
        decimal_amount = Decimal(0)
    else:
        decimal_amount = Decimal(str(amount))
    return decimal_amount.quantize(MONEY_QUANTIZE, rounding=CURRENCY_ROUNDING)

def auto_split_payment_movement(importo_totale_documento: Decimal, num_installments: int, start_date, interval_days: int = 30):
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

            'rma_' + 'data_scadenza':  datetime.strptime(start_date, '%Y-%m-%d').date() + timedelta(days=interval_days * (i + 1)),
            'rma_' + 'importo_pagamento': installment_amount,
            'rma_' + 'nome_cassa': '',
            'rma_' + 'notes': f'Rata {i + 1} di {num_installments}',
            'rma_' + 'data_pagamento': None  # Not paid yet
        }
        terms.append(term)

    return terms

# TODO: The problem here is that I add a lot of complexity
#  because I have to stop the streamlit execution when the
#  dialog is open and manually rerun() everything; but I
#  have to handle the fact that, at the rerun() point, every
#  variable that needs to be present in session_state is
#  up to date. For now I'll search for an easier solution.
def return_warning_modal(message, key):
    """
    Usage:
    is_modal_required, show_warning_modal = return_warning_modal(
                        message = "Tutti gli importi verranno reimpostati, procedere?",
                        key = 'reimposta_importi_movimenti')

                    if is_modal_required:
                        show_warning_modal()
    """
    is_modal_required = True

    unique_key = 'remember_dialog_' + key
    if unique_key not in st.session_state:
        st.session_state.unique_key = True

    if st.session_state.unique_key:

        @st.dialog('Attenzione')
        def show_warning_dialog():
            st.warning(message)

            if st.button('Procedi', key = unique_key + 'Procedi'):
                return True
            if st.button('Annulla', key = unique_key + 'Annulla'):
                return False

            if st.checkbox("Non ricordarmelo più"):
                st.session_state.unique_key = False

        return is_modal_required, show_warning_dialog

    else:
        is_modal_required = False
        return is_modal_required, None

def main():
    user_id, supabase_client, page_can_render = setup_page("Gestione Altri Movimenti")
    sommario, attivi, passivi, test = st.tabs(["Sommario", "Movimenti Attivi", "Movimenti Passivi", "Test"])

    if page_can_render:

        with sommario:
            # TODO; .eq('user_id', user_id) AM I ENFORCING THIS because the view will
            #  only select only the user's data?
            result = supabase_client.table('monthly_altri_movimenti_summary').select('*').execute()

            if not result.data:
                st.warning("Nessun dato disponibile per il periodo selezionato")
            else:
                # I need this else otherwise when I do df.columns[0] I get an Index error
                #TODO: value formatting
                df = pd.DataFrame(result.data)

                # Assumning that I force the first column of the view to be the index one.
                df = df.set_index(df.columns[0])
                # TODO; df.columns = ["Voce"] + df.columns[1:]

                df.columns = [
                    col.replace('_', ' ').title() if isinstance(col, str) else str(col)
                    for col in df.columns
                ]

                # TODO: scroll bar always preset, auto formatting everything to euro, remove some options.
                st.dataframe(df, use_container_width=True)

                fig = create_monthly_line_chart(df,"Movimenti Attivi", "Movimenti Passivi")
                st.plotly_chart(fig)


        with attivi:
            pass
            # render_movimenti_crud_page(supabase_client, user_id,
            #                            'movimenti_attivi', 'ma_',
            #                            'rma_',
            #                            altri_movimenti_config)
        with passivi:
            render_movimenti_crud_page(supabase_client, user_id,
                                       'movimenti_passivi', 'mp_',
                                       'rmp_',
                                       altri_movimenti_config)

        with test:
            # Selected movement is only used for knowing when to refetch data
            # from the terms table when the user changes selection.
            if 'selected_movement' not in st.session_state:
                st.session_state.selected_movement = None

            if 'test_terms' not in st.session_state:
                st.session_state.test_terms = None

            # This is for managing the 'Annulla' button
            # It will just store the first version fetched from the database.
            # The only two place where this is set should be:
            # After a successful save
            # When I change selection in the dataframe, the backup terms must correspond
            # to the terms of the new selection.
            if 'backup_terms' not in st.session_state:
                st.session_state.backup_terms = None











            movimenti_data = fetch_all_records(supabase_client, 'movimenti_attivi', user_id)
            if not movimenti_data:
                st.warning("Nessun movimento trovato. Creare un movimento prima di proseguire.")

            df = pd.DataFrame(movimenti_data)
            df.columns = [
                col.replace('_', ' ').title() if isinstance(col, str) else str(col)
                for col in df.columns
            ]
            df = df.drop(['Id', 'User Id', 'Created At', 'Updated At'], axis = 1)

            uppercase_prefixes = ['Fe ', 'Fr ', 'Rfe ', 'Rfr ', 'Ma ', 'Mp ', 'Rma ', 'Rmp ']
            def remove_prefix(col_name, prefixes):
                for prefix in prefixes:
                    if col_name.startswith(prefix):
                        return col_name[len(prefix):]
                return col_name  # Return original if no prefix found
            df.columns = [remove_prefix(col, uppercase_prefixes) for col in df.columns]

            selection = st.dataframe(df, use_container_width=True,
                                     selection_mode = 'single-row',
                                     on_select='rerun',
                                     hide_index = True,
                                     key = 'test_selection_df')








            col1, col2, col3, space = st.columns([1,1,1,4])
            with col1:
                add = st.button("Aggiungi Movimento", type='primary', key = 'movimenti_attivi' + 'add')
                if add:
                    render_add_modal(supabase_client, 'movimenti_attivi',
                                     altri_movimenti_config,
                                     'ma_')

            with col2:
                modify = st.button("Modifica Movimento", key = 'movimenti_attivi' + 'modify')
                if modify:
                    if selection.selection['rows']:
                        selected_index = selection.selection['rows'][0]
                        selected_row = movimenti_data[selected_index]
                        render_modify_modal(supabase_client, 'movimenti_attivi',
                                            altri_movimenti_config, selected_row, 'ma_')
                    else:
                        st.warning('Seleziona un movimento da modificare')

            with col3:
                delete = st.button("Rimuovi Movimento", key = 'movimenti_attivi' + 'delete')
                if delete:
                    if selection.selection['rows']:
                        selected_index = selection.selection['rows'][0]
                        selected_id = movimenti_data[selected_index]['id']
                        render_delete_modal(supabase_client, 'movimenti_attivi', selected_id)
                    else:
                        st.warning('Seleziona un movimento da eliminare')

            with st.expander("Visualizza e Gestisci Scadenze"):
                    # TODO: In order to help the user understand that the rows of the dataframe can be clicked,
                    #  start with the first checkbox selected.
                    if selection.selection['rows']:
                        st.write('Scadenze in modifica:')

                        selected_index = selection.selection['rows'][0]
                        record_data = movimenti_data[selected_index] # selected row

                        importo_totale_movimento = to_money(record_data['ma_' + 'importo_totale'])
                        numero_documento = record_data['ma_' + 'numero']
                        data_documento   = record_data['ma_' + 'data']
                        movement_key = {
                            'rma_numero': numero_documento,
                            'rma_data': data_documento
                        }




                        if st.session_state.test_terms is None or st.session_state.selected_movement != selection:
                            try:
                                result = supabase_client.table('rate_' + 'movimenti_attivi').select('*').eq('user_id', user_id) \
                                    .eq('rma_' + 'numero', record_data['ma_' + 'numero']) \
                                    .eq('rma_' + 'data', record_data['ma_' + 'data']).execute()

                                existing_terms = []
                                for row in result.data:
                                    term = {
                                        'rma_' + 'data_scadenza': datetime.strptime(row['rma_' + 'data_scadenza'], '%Y-%m-%d').date(),
                                        'rma_' + 'data_pagamento': datetime.strptime(row['rma_' + 'data_pagamento'], '%Y-%m-%d').date() if row['rma_' + 'data_pagamento'] else None,
                                        'rma_' + 'importo_pagamento': float(row['rma_' + 'importo_pagamento']),
                                        'rma_' + 'nome_cassa': row['rma_' + 'nome_cassa'] or '',
                                        'rma_' + 'notes': row['rma_' + 'notes'] or '',
                                    }
                                    existing_terms.append(term)
                                st.session_state.test_terms = existing_terms
                                st.session_state.selected_movement = selection
                                # This try should be triggered only on the first loading or when I change selection
                                # so it should be safe to reset the existing terms here.
                                st.session_state.backup_terms = existing_terms
                            except Exception as e:
                                st.error(f"Errore nel caricamento dei termini: {str(e)}")

                        terms_df = pd.DataFrame(st.session_state.test_terms)
                        terms_df.columns = [col[len('rma_'):].replace('_',' ').title() for col in terms_df.columns]

                        column_config = get_standard_column_config(money_columns = ['Importo Pagamento'],
                                                                   date_columns = ['Data Scadenza', 'Data Pagamento'])

                        column_config['Nome Cassa'] = st.column_config.SelectboxColumn(
                                    "Nome Cassa",
                                    options=[
                                        "Cassa 1",
                                        "Cassa 2",
                                        "Cassa 3"
                                    ],
                                    required=False)

                        column_config['Notes'] = st.column_config.TextColumn(
                                    "Notes",
                                    required=False)

                        edited = st.data_editor(terms_df,
                                       key = 'test_terms_df',
                                       column_config = column_config,
                                       hide_index = True,
                                       num_rows = 'dynamic')

                        # if st.button('double_test'):
                        #     doubled = []
                        #     for term in st.session_state.test_terms:
                        #         doubled.append(term)
                        #         doubled.append(term)
                        #     st.session_state.test_terms = doubled
                        #     st.rerun()

                        c1, c2,  c3, c4 = st.columns([3,3,1,1], vertical_alignment='bottom')
                        with c1:
                            with st.expander("Configurazione Iniziale Rapida", width=500):
                                st.write("""La configurazione rapida permette di generare automaticamente il
                                numero desiderato di scadenze con importo diviso ugualmente.""")
                                st.write("""Attenzione: questa operazione sovrascriverà tutti i campi delle
                                scadenze attualmente configurate.""")
                                split_col1, split_col2, split_col3 = st.columns([1, 1, 1],
                                                                                vertical_alignment='bottom')

                                with split_col1:
                                    num_installments = st.number_input("Numero rate", min_value=1, max_value=12, value=1)

                                with split_col2:
                                    interval_days = st.number_input("Giorni tra rate", min_value=1, max_value=365, value=30, step=15)

                                with split_col3:
                                    # TODO; can I put an help message over the button
                                    #  so that I don't have to handle the complexity of a dialog?
                                    if st.button("Applica"):

                                        up_to_date_terms = auto_split_payment_movement(
                                            importo_totale_movimento, num_installments, data_documento, interval_days
                                        )
                                        st.session_state.test_terms = up_to_date_terms
                                        st.rerun()
                        with c2:
                            with st.expander("Divisione Automatica Importo", width=500):
                                _edited = edited.copy()
                                _edited.columns = ['rma_' + col.replace(' ','_').lower() for col in _edited.columns]

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

                                if st.button("Dividi Importo"):

                                    total_allocated = Decimal('0.00')

                                    for i in range(movements_count):
                                        # Last installment gets the remainder to avoid rounding errors
                                        if i == movements_count - 1:
                                            up_to_date_terms[i]['rma_' + 'importo_pagamento'] = total_decimal - total_allocated
                                        else:
                                            up_to_date_terms[i]['rma_' + 'importo_pagamento'] = amount_per_installment
                                            total_allocated += amount_per_installment

                                    st.session_state.test_terms = up_to_date_terms
                                    st.rerun()
                        with c3:
                            if st.button("Salva  ", type='primary'):
                                def salva():
                                    try:
                                        terms = st.session_state.test_terms

                                        # Update terms, cannot do it in a function
                                        _edited = edited.copy()
                                        _edited.columns = ['rma_' + col.replace(' ','_').lower() for col in _edited.columns]
                                        up_to_date_terms = []
                                        for k,v in _edited.T.to_dict().items():
                                            up_to_date_terms.append(v)
                                        terms = up_to_date_terms


                                        # Verify total configured
                                        total_configured = to_money(0)
                                        for term in terms:
                                            total_configured += to_money(term['rma_' + 'importo_pagamento'])
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
                                            'rma_')
                                        for term in terms:
                                            errors = are_all_required_fields_present(term,
                                                                                     sql_table_fields_names,
                                                                                     altri_movimenti_config)
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
                                            'table_name': 'rate_' + 'movimenti_attivi',
                                            'delete_key': movement_key,
                                            'terms': terms_to_save
                                        }).execute()

                                        if result.data.get('success', False):
                                            st.success("Modifiche eseguite con successo")

                                            # I've tested it quicly, it seems to work.
                                            st.session_state.backup_terms = terms

                                            time.sleep(2)
                                            st.rerun()
                                        else:
                                            st.error(f'Errore nel salvataggio: {result}')

                                    # todo: fix error management / logging.
                                    #  Here is interesting because the above catches db error that are not
                                    #  exceptions, the below only exceptions.
                                    except Exception as e:
                                        st.error(f"Eccezione nel salvataggio: {str(e)}")

                                salva()
                        with c4:
                            if st.button('Annulla'):

                                # NOTE IMPORTANT: for some reason, if I do
                                # st.session_state.test_terms = st.session_state.backup_terms,
                                # the rerun() does not trigger the recomputing of the terms_df.
                                # I have to use a variable like undo_terms!
                                undo_terms = st.session_state.backup_terms
                                st.session_state.test_terms = undo_terms
                                st.rerun()

                    else:
                        st.warning('Seleziona un movimento per gestirne le rate')





if __name__ == '__main__':
    main()

