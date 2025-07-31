import streamlit as st
from xml_mapping_ricevute import XML_FIELD_MAPPING as fields_config
from invoice_utils import  render_data_table, render_modify_form



def main():

    st.set_page_config(
        page_title="Modifica Fatture Ricevute",
        page_icon="📄",
        layout="wide"
    )

    if 'user' not in st.session_state or not st.session_state.user:
        st.error("🔐 Please login first")
        st.stop()
    user_id = st.session_state.user['id']

    if 'client' not in st.session_state:
        st.error("Please create the client for pate_test_uploader")
        st.stop()
    supabase_client = st.session_state.client

    st.subheader('Modifica Fattura Ricevuta')

    selected_id = render_data_table(supabase_client, user_id, 'fatture_ricevute', fields_config, 'Fattura Ricevuta', search_enabled=False)
    if selected_id:
        st.write("---")
        render_modify_form(supabase_client, user_id, 'fatture_ricevute', fields_config, selected_id, 'Fattura Ricevuta')
    else:
        # st.info("👆 Seleziona un record dalla tabella per modificarlo")
        pass

if __name__ == "__main__":
    main()