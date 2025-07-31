import streamlit as st
from invoice_utils import render_xml_upload_section
from xml_mapping_emesse import XML_FIELD_MAPPING


def main():

    st.set_page_config(
        page_title="Upload Fatture Emesse",
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

    render_xml_upload_section(supabase_client, 'fatture_emesse', XML_FIELD_MAPPING, 'Fatture Emesse')

if __name__ == "__main__":
    main()