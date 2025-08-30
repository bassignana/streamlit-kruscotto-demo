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
def render_add_casse_modal(supabase_client, config):
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
def render_modify_casse_modal(supabase_client, config, selected_row):

    with st.form(f"modify_casse_form",
                 clear_on_submit=False,
                 enter_to_submit=False):
        form_data = {}

    for i, (field_name, field_config) in enumerate(config.items()):
        if field_name in ['c_nome_cassa','c_iban_cassa','c_descrizione_cassa']:
            record_value = selected_row.get(field_name, None)
            form_data[field_name] = render_field_widget(
                field_name, field_config, record_value,
                key_suffix=f"casse_anagrafica"
            )


    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Aggiorna", type="primary", key = 'casse_modify_modal_button'):
            try:
                # Validations
                error = ''
                if not any([form_data['c_nome_cassa'], form_data['c_iban_cassa']]):
                    error = 'Una cassa deve avere almeno un nome o un IBAN'

                if error:
                    st.warning(error)
                else:
                    for name, value in form_data.copy().items():
                        form_data[name] = str(value)

                    st.write(form_data)
                    with st.spinner("Salvataggio in corso..."):

                        #
                        #
                        #
                        #
                        # TODO: unique key contraint violation
                        #
                        #
                        #
                        result = supabase_client.table('casse').update(form_data) \
                            .eq('user_id', st.session_state.user.id) \
                            .execute()

                        # for name, value in form_data.items():
                        #     result = supabase_client.table('casse').update({name:value}) \
                        #         .eq('user_id', st.session_state.user.id) \
                        #         .execute()

                        has_errored = (hasattr(result, 'error') and result.error)

                        if not has_errored:
                            st.success("Dati aggiornati con successo!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Errore modifica cassa: {result.error.message}")
                            return

            except Exception as e:
                raise Exception(f'Error modifying cassa manually: {e}')

@st.dialog("Elimina cassa")
def render_delete_casse_modal(supabase_client, selected_row):
    col1, col2 = st.columns([1, 1])

    with col1:
        st.info("Rimuovere Casse presenti nelle fatture emesse nan avrà effetto in quanto attualmente non è un'operazione supportata")

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
    widget_key = 'anagrafica_azienda_'
    terms_key = widget_key + 'terms'

    if terms_key not in st.session_state:
        st.session_state[terms_key] = None

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
            render_add_casse_modal(supabase_client, config)

    with col2:
        if st.button("Modifica Cassa", key = '_modify_first_cassa'):
            if selection.selection['rows']:
                selected_index = selection.selection['rows'][0]
                selected_row = casse_data[selected_index]
                render_modify_casse_modal(supabase_client, config, selected_row)
            else:
                st.warning('Seleziona una cassa da modificare')

    with col3:
        if st.button("Elimina Cassa",  key = '_delete_first_cassa'):
            if selection.selection['rows']:
                selected_index = selection.selection['rows'][0]
                selected_row = casse_data[selected_index]
                st.write(selected_row)
                render_delete_casse_modal(supabase_client, selected_row)
            else:
                st.warning('Seleziona una cassa da eliminare')

def main():
    user_id, supabase_client = setup_page("Anagrafica Azienda",
                                                            '',
                                                           False)

    render_casse(supabase_client, altri_movimenti_config)

    # NOTE: Here I cannot use page_can_render, otherwise if the anagrafica
    # is not set, I'll go into a loop where I can never access the anagrafica form.
    # if page_can_render:
    render_anagrafica_azienda_form(supabase_client, user_id)

if __name__ == "__main__":
    main()