import streamlit as st
import logging
import os

from PIL import Image
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

def init_supabase():
    # url = st.secrets["SUPABASE_URL"]
    # key = st.secrets["SUPABASE_ANON_KEY"]
    # return create_client(url, key)
    if 'supabase_client' not in st.session_state:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_ANON_KEY"]
        st.session_state.supabase_client = create_client(url, key)

    return st.session_state.supabase_client


def main():
    im = Image.open("favicon.png")
    st.set_page_config(page_title="Kruscotto", page_icon=im, layout="wide")

    supabase_client = init_supabase()

    # This should be redundant.
    # if 'client' not in st.session_state:
    #     st.session_state.client = supabase_client
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

        # Hack. Find a better placement
        if 'force_update' not in st.session_state:
            st.session_state.force_update = False

        overview = st.Page("page_overview.py", title="Sommario Fatture", icon=":material/search:")

        upload = st.Page("invoice_uploader.py", title="Carica Fatture", icon=":material/upload:")
        fatture_manage = st.Page("invoice_manage.py", title="Fatture", icon=":material/receipt_long:")
        altri_movimenti_manage = st.Page("altri_movimenti_manage.py", title="Altri Movimenti", icon=":material/book_2:")

        flussi_di_cassa = st.Page("cash_flow.py", title="Flussi di Cassa", icon=":material/payments:")
        analisi_imposte = st.Page("analisi_imposte.py", title="Fatturato / Imposte", icon=":material/receipt:")

        profile = st.Page("page_profile.py", title="Utente", icon=":material/account_circle:")
        anagrafica_azienda = st.Page("page_anagrafica_azienda.py", title="Azienda", icon=":material/enterprise:")

        feedback = st.Page("page_feedback.py", title="Contattaci", icon=":material/chat:")


        pg = st.navigation(
            {
            # "Sommario": [overview],
            "Analisi": [flussi_di_cassa, analisi_imposte],
            "Documenti": [fatture_manage, upload, altri_movimenti_manage],
            "Profilo": [profile, anagrafica_azienda],
            "Contatti": [feedback],
            },
            position = 'top'
        )
        pg.run()

if __name__ == "__main__":
    main()


