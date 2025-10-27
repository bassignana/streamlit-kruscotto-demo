"""
Module created so I don't import from the streamlit_app.py which gets
the __name__ to __main__ when I do streamlit run streamlit_app.py
and can mess things up.
"""
import re
import time
import streamlit as st
import subprocess
import os
from supabase import create_client

# Safe path to the script (robust for deployment)
RESET_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "reset_password_secure.py")

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

def show_simple_login_form(supabase_client):
    """
    This is a standalone login form, used in tandem with the registration form or
    when a session is expired and I need to login again.
    """

    st.subheader("Login")
    with st.form("login", clear_on_submit=False, enter_to_submit=False, width=500):
        login_email = st.text_input("Email *", key="login_email")
        login_password = st.text_input("Password *", type="password", key="login_password")
        submitted = st.form_submit_button("Login", type="primary")

        if submitted:
            if not all([login_email, login_password]):
                st.error("Inserire tutti i campi")

            # NOTE: to access user object property, I can only use dot notation, not ['id'].
            user_obj, error_msg = login_user(supabase_client, login_email, login_password)
            if not error_msg:
                st.session_state.authenticated = True
                st.session_state.user = user_obj
                st.rerun()
            else:
                st.error(error_msg)

def show_login_and_render_form(supabase_client):
    """
    This is the main login and registration form, used on the initial login or registration.
    """

    space1, content, space2 = st.columns([1,1,1])

    with content:
        st.image("LogoK-Largo.png")

        tab1, tab2, tab3 = st.tabs(["Login", "Registrazione", "Reset Password"])

        with tab1:
            st.subheader(" ")

            show_simple_login_form(supabase_client)

        with tab2:
            st.subheader(" ")
            # Set clear_on_submit to False so the user does not have to fill again the
            # form if the email is already in use or if the password is not valid.
            with st.form("registration", clear_on_submit=False, enter_to_submit=False, width=500):
                signup_name = st.text_input("Nome", key="signup_name")
                signup_surname = st.text_input("Cognome", key="signup_full_name")
                signup_email = st.text_input("Email *", key="signup_email")
                signup_password = st.text_input("Password *", type="password", key="signup_password")
                signup_confirm_password = st.text_input("Conferma Password *", type="password", key="signup_confirm_password")
                submitted = st.form_submit_button("Registrati", type="primary")

                if submitted:
                    if not all([signup_email, signup_password, signup_confirm_password]):
                        st.error("Riempire tutti i campi obbligatori")
                        # TODO: rerunning here is bad UX, but for now this will do.
                        time.sleep(1)
                        return
                    elif signup_password != signup_confirm_password:
                        st.error("Le password non corrispondono")
                        time.sleep(1)
                        return
                    else:
                        is_email_valid, email_error_msg = validate_email(signup_email)
                        is_pwd_valid, pwd_error_msg = validate_password(signup_password)

                        if not is_email_valid:
                            st.error(email_error_msg)
                            time.sleep(1)
                            return
                        elif not is_pwd_valid:
                            st.error(pwd_error_msg)
                            time.sleep(1)
                            return
                        else:
                            full_name = None
                            if signup_name and signup_surname:
                                full_name = signup_name + ' ' + signup_surname

                            response, message = register_user(supabase_client, signup_email, signup_password, full_name)

                            # It seems, from a manual test, that an error during the sign up process will give
                            # an empty response and the error message.
                            if response:
                                st.success("Registrazione effettuata con successo. "
                                            "Cliccare sul tab Login per effettuare l'accesso.")
                                # st.rerun()
                                return
                                # todo
                                # I keep clear_on_submit in order to avoid the user re-entering
                                # both email and password if the registration fails.
                                # I would like to redirect to a login page though, but currently
                                # this is not done
                                # I've tested st.switch_page("cash_flow.py") but the page stays on
                                # the registration form.
                                # Also I've tried cleaning the form data, but
                                # clearing the form fields after successful registration gives:
                                # streamlit.errors.StreamlitAPIException:
                                # st.session_state.signup_name cannot be modified after
                                # the widget with key signup_name is instantiated.
                                # st.session_state.signup_name = ""
                                # st.session_state.signup_full_name = ""
                                # st.session_state.signup_email = ""
                                # st.session_state.signup_password = ""
                                # st.session_state.signup_confirm_password = ""
                            else:
                                st.error(message)
                                time.sleep(1)
                                return

        with tab3:
            # Done: Check in the source that the key does not get exposed.
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
            supabase_client = create_client(url, key)

            # NOTE; does not work in Streamlit, but it is a good flow.
            # This flow is secure because, even if I put another person email
            # I'm granted access to the reset password page from the link in the email
            # that I get. The link is made by a unique token that will grant me access to the
            # reset page. So I need to have access to the email account for resetting the
            # password.
            #
            # email = st.text_input('Email:', width = 300, key='reset_email_text_input')
            # if st.button('Invia email', type='primary'):
            #     supabase_client.auth.reset_password_for_email(
            #         email,
            #     )
            #     st.success('Controlla la tua casella di posta. Una mail per il reset della password sarà inviata a breve.')
            #     st.warning('Attenzione: controllare anche la casella della posta indesiderata (SPAM).')

            with st.form("reset_password", enter_to_submit=False):
                email = st.text_input("Email *")
                new_password = st.text_input("Nuova Password *", type="password")
                confirm_password = st.text_input("Conferma Password *", type="password")
                submit = st.form_submit_button("Reset Password")

                if submit:
                    if not email or not new_password:
                        st.error("Completa tutti i campi")
                    elif len(new_password) < 8:
                        st.error("La password deve avere almeno 8 caratteri")
                    elif new_password != confirm_password:
                        st.error("Le password non combaciano")
                    else:
                        try:
                            response = supabase_client.auth.admin.list_users()
                            user = next((u for u in response if u.email == email), None)

                            if not user:
                                st.error("L'email inserita non è associata a nessun utente")
                            else:
                                supabase_client.auth.admin.update_user_by_id(
                                    user.id,
                                    {"password": new_password}
                                )

                                st.success("Password ripristinata correttamente, è possibile procedere al login")

                        except Exception as e:
                            st.error(f"Error: {str(e)}")