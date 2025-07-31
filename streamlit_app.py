"""
In the main streamlit file, I want db and auth function definitions.
The rest are all imports.
"""

import streamlit as st
from supabase import create_client
import hashlib
import re
from datetime import datetime


@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength (minimum 8 characters, at least one number and one letter)"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"

def register_user(supabase_client, email, password, full_name):
    """Register a new user"""
    try:
        # Check if user already exists
        result = supabase_client.table('users').select('*').eq('email', email).execute()
        if result.data:
            return False, "User already exists with this email"
        
        # Hash password
        hashed_password = hash_password(password)
        
        # Insert new user
        user_data = {
            'email': email,
            'password_hash': hashed_password,
            'full_name': full_name,
            'created_at': datetime.now().isoformat(),
            'is_active': True
        }
        
        result = supabase_client.table('users').insert(user_data).execute()
        
        if result.data:
            return True, "User registered successfully"
        else:
            return False, "Registration failed"
            
    except Exception as e:
        return False, f"Registration error: {str(e)}"

def login_user(supabase_client, email, password):
    """Authenticate user login"""
    try:
        hashed_password = hash_password(password)
        
        result = supabase_client.table('users').select('*').eq('email', email).eq('password_hash', hashed_password).execute()
        
        if result.data:
            user = result.data[0]
            if user['is_active']:
                # Update last login
                supabase_client.table('users').update({
                    'last_login': datetime.now().isoformat()
                }).eq('id', user['id']).execute()
                
                return True, user
            else:
                return False, "Account is deactivated"
        else:
            return False, "Invalid email or password"
            
    except Exception as e:
        return False, f"Login error: {str(e)}"

def logout_user():
    """Clear session state and logout user"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

def main():
    st.set_page_config(page_title="Kruscotto", page_icon="", layout="wide")

    supabase_client = init_supabase()
    
    # Initialize session state
    if 'client' not in st.session_state:
        st.session_state.client = supabase_client
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    # Check if user is authenticated
    if not st.session_state.authenticated:
        st.title("🔐 Secure Authentication")
        
        # Create tabs for login and registration
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            st.header("Login")
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input("Password", type="password", key="login_password")
            
            if st.button("Login", type="primary"):
                if not login_email or not login_password:
                    st.error("Please fill in all fields")
                elif not validate_email(login_email):
                    st.error("Please enter a valid email address")
                else:
                    success, result = login_user(supabase_client, login_email, login_password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user = result
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error(result)
        
        with tab2:
            st.header("Register")
            reg_full_name = st.text_input("Full Name", key="reg_full_name")
            reg_email = st.text_input("Email", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_password")
            reg_confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm_password")
            
            if st.button("Register", type="primary"):
                if not all([reg_full_name, reg_email, reg_password, reg_confirm_password]):
                    st.error("Please fill in all fields")
                elif not validate_email(reg_email):
                    st.error("Please enter a valid email address")
                elif reg_password != reg_confirm_password:
                    st.error("Passwords do not match")
                else:
                    is_valid, message = validate_password(reg_password)
                    if not is_valid:
                        st.error(message)
                    else:
                        success, message = register_user(supabase_client, reg_email, reg_password, reg_full_name)
                        if success:
                            st.success(message)
                            st.info("Please login with your new credentials")
                        else:
                            st.error(message)
    
    else:
        # st.title(f"Welcome, {st.session_state.user['full_name']}!")

        # with st.sidebar:
        #     if st.button("Logout", type="secondary"):
        #         logout_user()

        overview = st.Page("page_overview.py", title="Sommario Fatture", icon=":material/search:")

        fatture_emesse_uploader = st.Page("emesse_uploader.py", title="Upload XML", icon=":material/search:")
        fatture_emesse_add = st.Page("emesse_add.py", title="Aggiungi", icon=":material/search:")
        fatture_emesse_modify = st.Page("emesse_modify.py", title="Modifica", icon=":material/search:")
        fatture_emesse_delete = st.Page("emesse_delete.py", title="Elimina", icon=":material/search:")

        fatture_ricevute_uploader = st.Page("ricevute_uploader.py", title="Upload XML", icon=":material/search:")
        fatture_ricevute_add = st.Page("ricevute_add.py", title="Aggiungi", icon=":material/search:")
        fatture_ricevute_modify = st.Page("ricevute_modify.py", title="Modifica", icon=":material/search:")
        fatture_ricevute_delete = st.Page("ricevute_delete.py", title="Elimina", icon=":material/search:")

        fatture_emesse_deadlines_add = st.Page("deadlines_add.py", title="Aggiungi", icon=":material/search:")
        fatture_emesse_deadlines_modify = st.Page("deadlines_modify.py", title="Modifica", icon=":material/search:")
        fatture_emesse_deadlines_delete = st.Page("deadlines_delete.py", title="Rimuovi", icon=":material/search:")
        fatture_emesse_deadlines_term_modify = st.Page("deadlines_terms_modify.py", title="Aggiorna Stato Pagamento", icon=":material/search:")

        feedback = st.Page("page_feedback.py", title="Contattaci", icon=":material/search:")


        pg = st.navigation(
            {
            "Sommario": [overview],
            "Fatture Emesse": [fatture_emesse_uploader, fatture_emesse_add, fatture_emesse_modify, fatture_emesse_delete],
            "Fatture Ricevute": [fatture_ricevute_uploader, fatture_ricevute_add, fatture_ricevute_modify, fatture_ricevute_delete],
            "Scadenze" : [fatture_emesse_deadlines_add, fatture_emesse_deadlines_modify, fatture_emesse_deadlines_delete, fatture_emesse_deadlines_term_modify],
            "Comunicazioni": [feedback]
            }
        )
        pg.run()

if __name__ == "__main__":
    main()


