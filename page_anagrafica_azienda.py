import streamlit as st

def render_anagrafica_azienda_form(client, user_id):

    try:
        response = client.table('user_data').select('codice_fiscale', 'partita_iva').eq('user_id', user_id).execute()
        existing_data = response.data[0] if response.data else None
    except Exception as e:
        st.error(f"Errore nel recupero dei dati: {str(e)}")
        existing_data = None

    existing_cf = existing_data['codice_fiscale'] if existing_data else ''
    existing_piva = existing_data['partita_iva'] if existing_data else ''

    with st.form('anagrafiche',clear_on_submit=False, enter_to_submit=False):
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
                        'codice_fiscale': cf_clean,
                        'partita_iva': piva_clean
                    }).eq('user_id', user_id).execute()

                    if result.data:
                        st.success("Dati aggiornati con successo!")
                    else:
                        st.error("Errore durante l'aggiornamento")
                        return

                else:
                    result = client.table('user_data').insert({
                        'user_id': user_id,
                        'codice_fiscale': cf_clean,
                        'partita_iva': piva_clean
                    }).execute()

                    if result.data:
                        st.success("Dati inseriti con successo!")
                    else:
                        st.error("Errore durante l'inserimento")
                        return
                st.rerun()

            except Exception as e:
                st.error(f"Errore upsert anagrafica azienda: {str(e)}")

def main():

    st.set_page_config(
        page_title="Anagrafica azienda",
        page_icon="",
        layout="wide"
    )

    if 'user' not in st.session_state or not st.session_state.user:
        st.error("🔐 Please login first")
        st.stop()
    user_id = st.session_state.user.id

    if 'client' not in st.session_state:
        st.error("Please create the client for pate_test_uploader")
        st.stop()
    supabase_client = st.session_state.client

    render_anagrafica_azienda_form(supabase_client, user_id)

if __name__ == "__main__":
    main()