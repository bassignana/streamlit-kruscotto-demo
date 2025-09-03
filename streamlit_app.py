import streamlit as st
import logging
import os
from supabase import create_client
from auth_utils import show_login_and_render_form

def setup_logging():
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        handlers=[
            logging.StreamHandler(),
            # logging.FileHandler('cashflow_app.log')
        ]
    )

setup_logging()
# Development: LOG_LEVEL=DEBUG streamlit run app.py
# Production: LOG_LEVEL=INFO streamlit run app.py
# logging.basicConfig(level=logging.DEBUG)    # Shows everything
# logging.basicConfig(level=logging.INFO)     # Shows info, warning, error, critical
# logging.basicConfig(level=logging.WARNING)  # Shows warning, error, critical (default)
# logging.basicConfig(level=logging.ERROR)    # Shows error, critical only
# logging.basicConfig(level=logging.CRITICAL) # Shows critical only

@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)



def main():
    st.set_page_config(page_title="Kruscotto", page_icon="", layout="wide")

    supabase_client = init_supabase()
    
    if 'client' not in st.session_state:
        st.session_state.client = supabase_client
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None

    # Add a flag to track login processing to prevent login form UI duplication after submit.
    if 'login_processing' not in st.session_state:
        st.session_state.login_processing = False

    if not st.session_state.authenticated:
        show_login_and_render_form(supabase_client)
    else:

        overview = st.Page("page_overview.py", title="Sommario Fatture", icon=":material/search:")

        fatture_manage = st.Page("invoice_manage.py", title="Fatture", icon=":material/book_2:")
        altri_movimenti_manage = st.Page("altri_movimenti_manage.py", title="Altri Movimenti", icon=":material/book_2:")

        flussi_di_cassa = st.Page("cash_flow.py", title="Flussi di Cassa", icon=":material/payments:")

        profile = st.Page("page_profile.py", title="Utente", icon=":material/account_circle:")
        anagrafica_azienda = st.Page("page_anagrafica_azienda.py", title="Azienda", icon=":material/enterprise:")

        feedback = st.Page("page_feedback.py", title="Contattaci", icon=":material/chat:")


        pg = st.navigation(
            {
            # "Sommario": [overview],
            "Documenti": [fatture_manage, altri_movimenti_manage],
            "Analisi": [flussi_di_cassa],
            "Profilo": [profile, anagrafica_azienda],
            "Contatti": [feedback],


            },
            position = 'top'
        )
        pg.run()

if __name__ == "__main__":
    main()


