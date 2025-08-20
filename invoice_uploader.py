import streamlit as st
from invoice_utils import render_generic_xml_upload_section
from utils import setup_page


def main():
    user_id, supabase_client, page_can_render = setup_page()

    if page_can_render:
        render_generic_xml_upload_section(supabase_client, user_id)

if __name__ == "__main__":
    main()