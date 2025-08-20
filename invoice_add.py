import streamlit as st
from utils import setup_page
from invoice_xml_mapping import XML_FIELD_MAPPING as fields_config
from invoice_utils import  render_add_form

def main():
    user_id, supabase_client, page_can_render = setup_page("Aggiungi Fatture")

    emesse, ricevute = st.tabs(["Aggiungi Fattura Emessa", "Aggiungi Fattura Ricevuta"])

    with emesse:
        render_add_form(supabase_client, 'fatture_emesse', fields_config, 'fe_')
    with ricevute:
        render_add_form(supabase_client, 'fatture_ricevute', fields_config,'fr_')

if __name__ == "__main__":
    main()