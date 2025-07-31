import streamlit as st
from xml_mapping_emesse import XML_FIELD_MAPPING as fields_config
from invoice_utils import  render_add_form

def main():

    st.set_page_config(
        page_title="Aggiungi Fattura Ricevuta",
        page_icon="📄",
        layout="wide"
    )

    if 'user' not in st.session_state or not st.session_state.user:
        st.error("🔐 Please login first")
        st.stop()

    if 'client' not in st.session_state:
        st.error("Please create the client for pate_test_uploader")
        st.stop()
    supabase_client = st.session_state.client

    render_add_form(supabase_client, 'fatture_ricevute', fields_config, 'Fattura Ricevuta')

if __name__ == "__main__":
    main()