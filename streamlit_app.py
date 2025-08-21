import streamlit as st
from supabase import create_client
import re
import time
import logging
import os

def setup_logging():
    log_level = os.getenv('LOG_LEVEL', 'DEBUG').upper()

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

def validate_email(email):
    # todo: better pattern, like in https://stackoverflow.com/questions/201323/how-can-i-validate-an-email-address-using-a-regular-expression
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email) is not None:
        return True, ""
    else:
        return False, "Inserire un indirizzo email valido"

def validate_password(password):

    msg = "La Password deve contenere almeno 8 caratteri, di cui almeno un numero"
    if len(password) < 8:
        return False, msg
    if not re.search(r'[A-Za-z]', password):
        return False, msg
    if not re.search(r'\d', password):
        return False, msg
    return True, ""

def register_user(supabase_client, email, password, full_name = None):
    try:
        response = supabase_client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name or ""
                }
            }
        })

        return response, ""

    except Exception as e:
        # "User already registered" is returned as str(e).
        if "already registered" in str(e):
            return {}, f"Errore, email già registrata"
        else:
            return {}, f"Errore durante la registrazione, eccezione: {str(e)}"

def login_user(supabase_client, email, password):
    try:

        response = supabase_client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        return response.user, ""

    except Exception as e:
        if "Invalid login credentials" in str(e):
            return {}, f"Credenziali di accesso non valide"
        else:
            return {}, f"Errore: {str(e)}"

# def logout_user():
#     """Clear session state and logout user"""
#     for key in list(st.session_state.keys()):
#         del st.session_state[key]
#     st.rerun()

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

    # Check if user is authenticated, else show login and registration forms.
    if not st.session_state.authenticated:
        st.subheader("Autenticazione")
        
        # Create tabs for login and registration
        tab1, tab2 = st.tabs(["Login", "Registrazione"])
        
        with tab1:
            st.header("Login")

            # Show a loading state during login processing to prevent duplication
            if st.session_state.login_processing:
                st.info("Accesso in corso...")
                # Small delay to prevent UI flicker
                time.sleep(2)
                st.session_state.login_processing = False
                st.rerun()
            else:
                with st.form("login", clear_on_submit=True, enter_to_submit=False):
                    login_email = st.text_input("Email *", key="login_email")
                    login_password = st.text_input("Password *", type="password", key="login_password")
                    submitted = st.form_submit_button("Login", type="primary")

                    if submitted:
                        if not all([login_email, login_password]):
                            st.error("Inserire tutti i campi")
                        else:
                            # Set processing flag to show loading state
                            st.session_state.login_processing = True

                        # NOTE: to access user object property, I can only use dot notation, not ['id'].
                        user_obj, error_msg = login_user(supabase_client, login_email, login_password)
                        if not error_msg:
                            st.session_state.authenticated = True
                            st.session_state.user = user_obj
                            st.session_state.login_processing = False
                            st.success("Login successful!")
                            # Add a small delay before rerun to ensure state is properly set
                            time.sleep(0.3)
                            st.rerun()
                        else:
                            st.error(error_msg)
        
        with tab2:
            st.header("Registrazione")
            # Set clear_on_submit to False so the user does not have to fill again the
            # form if the email is already in use or if the password is not valid.
            with st.form("registration", clear_on_submit=False, enter_to_submit=False):
                signup_name = st.text_input("Nome", key="signup_name")
                signup_surname = st.text_input("Cognome", key="signup_full_name")
                signup_email = st.text_input("Email *", key="signup_email")
                signup_password = st.text_input("Password *", type="password", key="signup_password")
                signup_confirm_password = st.text_input("Conferma Password *", type="password", key="signup_confirm_password")
                submitted = st.form_submit_button("Registrati", type="primary")

                if submitted:
                    if not all([signup_email, signup_password, signup_confirm_password]):
                        st.error("Riempire tutti i campi obbligatori")
                    elif signup_password != signup_confirm_password:
                        st.error("Le password non corrispondono")
                    else:
                        is_email_valid, email_error_msg = validate_email(signup_email)
                        is_pwd_valid, pwd_error_msg = validate_password(signup_password)

                        if not is_email_valid:
                            st.error(email_error_msg)
                        elif not is_pwd_valid:
                            st.error(pwd_error_msg)
                        else:
                            full_name = None
                            if signup_name is not None and signup_surname is not None:
                                full_name = signup_name + ' ' + signup_surname

                            response, message = register_user(supabase_client, signup_email, signup_password, full_name)
                            if response:
                                st.success("Registrazione effettuata con successo.")

                                # Clear the form fields after successful registration for better UX.
                                st.session_state.signup_name = ""
                                st.session_state.signup_full_name = ""
                                st.session_state.signup_email = ""
                                st.session_state.signup_password = ""
                                st.session_state.signup_confirm_password = ""
                            else:
                                st.error(message)

    else:
        # st.title(f"Welcome, {st.session_state.user['full_name']}!")

        # with st.sidebar:
        #     if st.button("Logout", type="secondary"):
        #         logout_user()

        overview = st.Page("page_overview.py", title="Sommario Fatture", icon=":material/search:")

        anagrafica_azienda = st.Page("page_anagrafica_azienda.py", title="Azienda", icon=":material/search:")

        fatture_upload = st.Page("invoice_uploader.py", title="Carica", icon=":material/search:")
        fatture_overview = st.Page("invoice_overview.py", title="Sommario", icon=":material/search:")
        fatture_emesse_add = st.Page("invoice_add.py", title="Aggiungi", icon=":material/search:")
        fatture_emesse_modify = st.Page("invoice_modify.py", title="Modifica", icon=":material/search:")
        fatture_emesse_delete = st.Page("invoice_delete.py", title="Elimina", icon=":material/search:")
        fatture_deadlines_manage = st.Page("invoice_deadlines.py", title="Gestisci Rate", icon=":material/search:")

        altri_movimenti_manage = st.Page("altri_movimenti_manage.py", title="Gestisci Movimenti", icon=":material/search:")

        flussi_di_cassa = st.Page("cash_flow.py", title="Flussi di Cassa", icon=":material/search:")

        feedback = st.Page("page_feedback.py", title="Contattaci", icon=":material/search:")


        pg = st.navigation(
            {
            # "Sommario": [overview],
            "Anagrafiche": [anagrafica_azienda],
            "Fatture": [fatture_overview, fatture_upload, fatture_emesse_add, fatture_emesse_modify, fatture_emesse_delete, fatture_deadlines_manage],
            "Altri Movimenti": [altri_movimenti_manage],
            "Flussi di Cassa": [flussi_di_cassa],
            "Comunicazioni": [feedback]
            }
        )
        pg.run()

if __name__ == "__main__":
    main()


