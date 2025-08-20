import streamlit as st

def setup_page(page_title = "", page_icon = ""):
    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout="wide"
    )

    if 'user' not in st.session_state or not st.session_state.user:
        st.error("🔐 Please login first")
        st.stop()
    user_id = st.session_state.user.id

    if 'client' not in st.session_state:
        st.error("Please create the client for invoice_uploader")
        st.stop()
    supabase_client = st.session_state.client

    response = supabase_client.table('user_data').select("*").eq('user_id',user_id).execute()

    # Flag for avoiding rendering the page content in case the anagrafica azienda is not set yet.
    page_can_render = True
    if len(response.data) < 1:
        page_can_render = False
        st.warning("Prima di usare l'applicazione e' necessario impostare l'anagrafica azienda")
        switched = st.button("Imposta Anagrafica Azienda", type='primary')
        if switched:
            st.switch_page("page_anagrafica_azienda.py")


    return user_id, supabase_client, page_can_render

def extract_field_names(sql_file_path ='sql/02_create_tables.sql', prefix='fe_'):
    field_names = []
    with open(sql_file_path, 'r') as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith(prefix):
                # Get first word (field name)
                field_name = stripped.split()[0]
                # Remove prefix because I have to check against field names in
                # the xml_fields which has names without prefix.
                field_name = field_name[len(prefix):]
                field_names.append(field_name)
    return field_names

def extract_prefixed_field_names(sql_file_path = 'sql/02_create_tables.sql', prefix='fe_'):
    field_names = []
    with open(sql_file_path, 'r') as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith(prefix):
                # Get first word (field name)
                field_name = stripped.split()[0]
                field_names.append(field_name)
    return field_names