import logging

import streamlit as st
import time
import pandas as pd

from altri_movimenti_config import altri_movimenti_config
from altri_movimenti_utils import remove_prefix
from config import uppercase_prefixes, technical_fields
from invoice_utils import render_field_widget
from utils import setup_page, fetch_all_records_from_view


def render_anagrafica_azienda_form(client, user_id):

    try:
        response = client.table('user_data').select('ud_codice_fiscale', 'ud_partita_iva').eq('user_id', user_id).execute()
        existing_data = response.data[0] if response.data else None
    except Exception as e:
        st.error(f"Errore nel recupero dei dati: {str(e)}")
        existing_data = None

    existing_cf = existing_data['ud_codice_fiscale'] if existing_data else ''
    existing_piva = existing_data['ud_partita_iva'] if existing_data else ''

    with st.form('anagrafiche',clear_on_submit=False, enter_to_submit=False, width=500):
        codice_fiscale = st.text_input('Codice Fiscale *', placeholder='es. BSSTMS96T27B885E', value=existing_cf, key='codice_fiscale')
        partita_iva = st.text_input('Partita IVA *', placeholder='es. 1234567890', value=existing_piva, key='partita_iva')
        submitted = st.form_submit_button("Imposta", type="primary")

        if submitted:
            if not all([codice_fiscale.strip(), partita_iva.strip()]):
                st.error("Inserire tutti i campi obbligatori")
                return

            cf_clean = codice_fiscale.strip().upper()
            piva_clean = partita_iva.strip()

            try:
                if existing_data:
                    result = client.table('user_data').update({
                        'ud_codice_fiscale': cf_clean,
                        'ud_partita_iva': piva_clean
                    }).eq('user_id', user_id).execute()

                    if result.data:
                        st.success("Dati aggiornati con successo!")
                        time.sleep(2)
                    else:
                        st.error("Errore durante l'aggiornamento")
                        return

                else:
                    result = client.table('user_data').insert({
                        'user_id': user_id,
                        'ud_codice_fiscale': cf_clean,
                        'ud_partita_iva': piva_clean
                    }).execute()

                    if result.data:
                        st.success("Dati inseriti con successo!")
                        time.sleep(2)
                    else:
                        st.error("Errore durante l'inserimento")
                        return
                st.rerun()

            except Exception as e:
                st.error(f"Errore upsert anagrafica azienda: {str(e)}")

@st.dialog("Aggiungi cassa")
def render_add_casse_modal(supabase_client, config, emesse_names, emesse_iban):
    with st.form('add_casse_form',
                 clear_on_submit=False,
                 enter_to_submit=False):

        form_data = {}
        for i, (field_name, field_config) in enumerate(config.items()):
                if field_name in ['c_nome_cassa','c_iban_cassa','c_descrizione_cassa']:
                    form_data[field_name] = render_field_widget(
                        field_name, field_config, key_suffix=f"casse_anagrafica"
                    )

        if st.form_submit_button("Aggiungi", type="primary"):
            try:
                # Validations
                error = ''
                if not any([form_data['c_nome_cassa'], form_data['c_iban_cassa']]):
                    error = 'Una cassa deve avere almeno un nome o un IBAN'
                elif form_data['c_nome_cassa'] in emesse_names:
                    error = 'Il nome inserito è già presente in una fattura emessa'
                elif form_data['c_iban_cassa'] in emesse_iban:
                    error = "L'IBAN inserito è già presente in una fattura emessa."

                if error:
                    st.warning(error)
                else:
                    for name, value in form_data.copy().items():
                        form_data[name] = str(value)

                    with st.spinner("Salvataggio in corso..."):
                        form_data['user_id'] = st.session_state.user.id

                        result = supabase_client.table('casse').insert(form_data).execute()

                        has_errored = (hasattr(result, 'error') and result.error)

                        if not has_errored:
                            st.success("Dati inseriti con successo!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Errore inserimento cassa: {result.error.message}")
                            return

            except Exception as e:
                raise Exception(f'Error adding cassa manually: {e}')

@st.dialog("Modifica cassa")
def render_modify_casse_modal(supabase_client, config, selected_row, emesse_names, emesse_iban):

    with st.form(f"modify_casse_form",
                 clear_on_submit=False,
                 enter_to_submit=False):
        form_data = {}

    #
    #
    #
    # TODO; hack:
    #  if is read from emesse, get select count, if 0, insert else update with record.
    #  Test in console first to be sure that there is no problem with table constraints.
    #
    #
    #
    is_read_from_emesse = selected_row['c_nome_cassa'] in emesse_names or selected_row['c_iban_cassa'] in emesse_iban

    if is_read_from_emesse:
        st.info('Attualmente, per le casse lette da fatture emesse, è possibile modificare solo la descrizione')

        # for i, (field_name, field_config) in enumerate(config.items()):
        #     if field_name in ['c_descrizione_cassa']:
        #         record_value = selected_row.get(field_name, None)
        #         form_data[field_name] = render_field_widget(
        #             field_name, field_config, record_value,
        #             key_suffix=f"casse_anagrafica"
        #         )

    # else:

    for i, (field_name, field_config) in enumerate(config.items()):
        if field_name in ['c_nome_cassa','c_iban_cassa','c_descrizione_cassa']:
            record_value = selected_row.get(field_name, None)

            if is_read_from_emesse and field_name in ['c_nome_cassa','c_iban_cassa']:
                form_data[field_name] = render_field_widget(
                    field_name, field_config, record_value,
                    key_suffix=f"casse_anagrafica",
                    disabled = True
                )
            else:
                form_data[field_name] = render_field_widget(
                    field_name, field_config, record_value,
                    key_suffix=f"casse_anagrafica",
                    disabled = False
                )



    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Aggiorna", type="primary", key = 'casse_modify_modal_button'):

                error = ''
                # if 'c_nome_cassa' in form_data or 'c_iban_cassa' in form_data:
                if not any([form_data['c_nome_cassa'], form_data['c_iban_cassa']]):
                    error = 'Una cassa deve avere almeno un nome o un IBAN'

                if error:
                    st.warning(error)
                else:
                    for name, value in form_data.copy().items():
                        form_data[name] = str(value)

                    form_data['user_id'] = st.session_state.user.id

                try:

                    with st.spinner("Salvataggio in corso..."):
                        delete_query = supabase_client.table('casse').delete()
                        st.write(form_data)
                        for k,v in form_data.items():
                            delete_query = delete_query.eq(k,v)
                        st.write(delete_query)
                        result = delete_query.execute()
                        st.write(result)
                        time.sleep(20)
                        result = supabase_client.table('casse').insert(form_data).execute()

                        has_errored = (hasattr(result, 'error') and result.error)

                        # todo: I don't know if has_errored works for all types of errors...
                        if not has_errored:
                            st.success("Dati aggiornati con successo!")
                            st.rerun()
                        else:
                            st.error(f"Errore modifica cassa: {result.error.message}")
                            return

                except Exception as e:
                    raise Exception(f'Error modifying cassa manually: {e}')

@st.dialog("Elimina cassa")
def render_delete_casse_modal(supabase_client, selected_row, emesse_names, emesse_iban):

    error = ''
    if selected_row['c_nome_cassa'] in emesse_names:
        error = 'Non è al momento supportato eliminare una cassa che è stata letta da una fattura emessa'
    elif selected_row['c_iban_cassa'] in emesse_iban:
        error = 'Non è al momento supportato eliminare una cassa che è stata letta da una fattura emessa'

    if error:
        st.warning(error)
        return
    else:

        if st.button("Elimina", type="primary", key = 'casse_delete_modal_button'):
            try:
                with st.spinner("Salvataggio in corso..."):

                    # Here I have to build the query because reading from a view,
                    # I don't have an id to identify the record.
                    query = supabase_client.table('casse').delete()
                    for field, value in selected_row.items():
                        query = query.eq(field, value)

                    result = query.eq('user_id', st.session_state.user.id).execute()

                    has_errored = (hasattr(result, 'error') and result.error)

                    if not has_errored:
                        st.success("Dati eliminati con successo!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Errore rimozione cassa: {result.error.message}")
                        return

            except Exception as e:
                raise Exception(f'Error deleting cassa manually: {e}')


def render_casse(supabase_client, config):
    # widget_key = 'anagrafica_azienda_'
    # terms_key = widget_key + 'terms'
    # if terms_key not in st.session_state:
    #     st.session_state[terms_key] = None

    emesse_names_result = supabase_client.table('rate_fatture_emesse').select('rfe_nome_cassa') \
                                  .eq('user_id', st.session_state.user.id) \
                                  .execute()
    emesse_names = []
    for item in emesse_names_result.data:
        v = item.get('rfe_nome_cassa')
        if v is not None and v not in emesse_names:
            emesse_names.append(v)

    emesse_iban_result = supabase_client.table('rate_fatture_emesse').select('rfe_iban_cassa') \
                                  .eq('user_id', st.session_state.user.id) \
                                  .execute()
    emesse_iban = []
    for item in emesse_iban_result.data:
        v = item.get('rfe_iban_cassa')
        if v is not None and v not in emesse_iban:
            emesse_iban.append(v)

    casse_data = fetch_all_records_from_view(supabase_client, 'casse_summary')

    # TODO: test
    if not casse_data:
        st.warning("Nessuna cassa trovata. Creare una fattura emessa oppure aggiungere manualmente una cassa.")
        if st.button("Aggiungi Cassa", type='primary', key = '_add_first_cassa'):
            render_add_casse_modal(supabase_client, config)
        return

    casse_df = pd.DataFrame(casse_data)

    casse_df.columns = [
        col.replace('_', ' ').title() if isinstance(col, str) else str(col)
        for col in casse_df.columns
    ]

    for tech_field in technical_fields:
        if tech_field in casse_df.columns:
            casse_df = casse_df.drop([tech_field], axis = 1)

    casse_df.columns = [remove_prefix(col, uppercase_prefixes) for col in casse_df.columns]

    selection = st.dataframe(casse_df, use_container_width=True,
                             selection_mode = 'single-row',
                             on_select='rerun',
                             hide_index = True,
                             key = 'casse_selection_df')

    col1, col2, col3, space = st.columns([1,1,1,4])

    with col1:
        if st.button("Aggiungi Cassa", type='primary', key = '_add_first_cassa'):
            render_add_casse_modal(supabase_client, config, emesse_names, emesse_iban)

    with col2:
        if st.button("Modifica Cassa", key = '_modify_first_cassa'):
            if selection.selection['rows']:
                selected_index = selection.selection['rows'][0]
                selected_row = casse_data[selected_index]
                render_modify_casse_modal(supabase_client, config, selected_row, emesse_names, emesse_iban)
            else:
                st.warning('Seleziona una cassa da modificare')

    with col3:
        if st.button("Elimina Cassa",  key = '_delete_first_cassa'):
            if selection.selection['rows']:
                selected_index = selection.selection['rows'][0]
                selected_row = casse_data[selected_index]
                render_delete_casse_modal(supabase_client, selected_row, emesse_names, emesse_iban)
            else:
                st.warning('Seleziona una cassa da eliminare')

def main():
    user_id, supabase_client = setup_page("Anagrafica Azienda",
                                                            '',
                                                           False)
    tab1, tab2 = st.tabs(["Anagrafica Azienda", "Casse"])
    with tab1:
        # NOTE: Here I cannot use page_can_render, otherwise if the anagrafica
        # is not set, I'll go into a loop where I can never access the anagrafica form.
        # if page_can_render:
        render_anagrafica_azienda_form(supabase_client, user_id)

    # page_can_render situation: for now I'll leave such that if an anagrafica is not
    # present then it will throw no errors. Maybe correct this at 1.0
    with tab2:
        render_casse(supabase_client, altri_movimenti_config)



if __name__ == "__main__":
    main()