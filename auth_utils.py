"""
Module created so I don't import from the streamlit_app.py which gets
the __name__ to __main__ when I do streamlit run streamlit_app.py
and can mess things up.
"""
import re
import time
import streamlit as st


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
    # st.header("Kruscotto")

    st.image("Logo20250818.jpeg")

    tab1, tab2 = st.tabs(["Login", "Registrazione"])

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
                    return
                elif signup_password != signup_confirm_password:
                    st.error("Le password non corrispondono")
                    return
                else:
                    is_email_valid, email_error_msg = validate_email(signup_email)
                    is_pwd_valid, pwd_error_msg = validate_password(signup_password)

                    if not is_email_valid:
                        st.error(email_error_msg)
                        return
                    elif not is_pwd_valid:
                        st.error(pwd_error_msg)
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
                            return