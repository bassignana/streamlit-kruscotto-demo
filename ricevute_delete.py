import streamlit as st

from invoice_utils import render_data_table, render_delete_confirmation
from xml_mapping_ricevute import XML_FIELD_MAPPING as fields_config

def main():

    st.set_page_config(
        page_title="Rimuovi Fattura Ricevuta",
        page_icon="📄",
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

    st.subheader('Elimina Fattura Ricevuta')

    selected_id = render_data_table(supabase_client, user_id, 'fatture_ricevute', fields_config, 'Fattura Ricevuta', search_enabled=False)
    if selected_id:
        st.write("---")
        render_delete_confirmation(supabase_client, user_id, 'fatture_ricevute', fields_config, selected_id, 'Fattura Ricevuta')
    else:
        # st.info("👆 Seleziona un record dalla tabella per eliminarlo")
        pass


if __name__ == "__main__":
    main()