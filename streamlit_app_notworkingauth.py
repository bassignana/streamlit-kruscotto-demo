import streamlit as st
import pandas as pd
import supabase
from supabase import create_client, Client
import hashlib
import re
from datetime import datetime, timedelta
import json


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

def get_user_data(supabase_client, user_id):
    """Get user-specific data from database"""
    try:
        # Example: Get user profile and related data
        result = supabase_client.table('user_data').select('*').eq('user_id', user_id).execute()
        return result.data
    except Exception as e:
        st.error(f"Error fetching user data: {str(e)}")
        return []

def save_user_data(supabase_client, user_id, data):
    """Save user-specific data to database"""
    try:
        data_entry = {
            'user_id': user_id,
            'data': json.dumps(data),
            'updated_at': datetime.now().isoformat()
        }
        
        # Check if data exists for this user
        existing = supabase_client.table('user_data').select('*').eq('user_id', user_id).execute()
        
        if existing.data:
            # Update existing data
            result = supabase_client.table('user_data').update(data_entry).eq('user_id', user_id).execute()
        else:
            # Insert new data
            result = supabase_client.table('user_data').insert(data_entry).execute()
            
        return True
    except Exception as e:
        st.error(f"Error saving user data: {str(e)}")
        return False

def logout_user():
    """Clear session state and logout user"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


########## auth ###############
import streamlit as st
from supabase import create_client, Client
from typing import Optional, Tuple
import re

# =====================================================
# CONFIGURATION
# =====================================================

def init_supabase() -> Client:
    """Initialize Supabase client with credentials from Streamlit secrets"""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_ANON_KEY"]
        return create_client(url, key)
    except KeyError as e:
        st.error(f"Missing Supabase credential: {e}")
        st.info("Add SUPABASE_URL and SUPABASE_ANON_KEY to your Streamlit secrets")
        st.stop()

# =====================================================
# SESSION MANAGEMENT
# =====================================================

def init_session_state():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None

def check_existing_session(supabase: Client) -> bool:
    """Check if user has valid existing session"""
    try:
        # Get current session from Supabase
        session = supabase.auth.get_session()
        
        if session and session.user:
            st.session_state.authenticated = True
            st.session_state.user = session.user
            st.session_state.user_email = session.user.email
            return True
        else:
            clear_session()
            return False
    except Exception:
        clear_session()
        return False

def clear_session():
    """Clear all session state"""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.user_email = None

def logout(supabase: Client):
    """Logout user and clear session"""
    try:
        supabase.auth.sign_out()
    except Exception:
        pass  # Continue even if logout fails
    finally:
        clear_session()
        st.rerun()

# =====================================================
# AUTHENTICATION FUNCTIONS
# =====================================================

def validate_email(email: str) -> bool:
    """Basic email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def register_user(supabase: Client, email: str, password: str) -> Tuple[bool, str]:
    """Register new user"""
    try:
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if response.user:
            if response.user.email_confirmed_at:
                # User is immediately confirmed
                st.session_state.authenticated = True
                st.session_state.user = response.user
                st.session_state.user_email = response.user.email
                return True, "Registration successful! Welcome!"
            else:
                # User needs email confirmation
                return True, "Registration successful! Please check your email to confirm your account."
        else:
            return False, "Registration failed. Please try again."
            
    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower():
            return False, "Email already registered. Please try logging in instead."
        elif "password" in error_msg.lower():
            return False, "Password too weak. Please choose a stronger password."
        else:
            return False, f"Registration failed: {error_msg}"

def login_user(supabase: Client, email: str, password: str) -> Tuple[bool, str]:
    """Login existing user"""
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user:
            st.session_state.authenticated = True
            st.session_state.user = response.user
            st.session_state.user_email = response.user.email
            return True, "Login successful!"
        else:
            return False, "Invalid email or password."
            
    except Exception as e:
        error_msg = str(e)
        if "invalid" in error_msg.lower():
            return False, "Invalid email or password."
        elif "not confirmed" in error_msg.lower():
            return False, "Please confirm your email address before logging in."
        else:
            return False, f"Login failed: {error_msg}"

def reset_password(supabase: Client, email: str) -> Tuple[bool, str]:
    """Send password reset email"""
    try:
        supabase.auth.reset_password_email(email)
        return True, "Password reset email sent! Check your inbox."
    except Exception as e:
        return False, f"Failed to send reset email: {str(e)}"

# =====================================================
# UI COMPONENTS
# =====================================================

def render_auth_form(supabase: Client):
    """Render authentication form with tabs for login/register/reset"""
    
    st.title("🔐 Authentication")
    
    tab1, tab2, tab3 = st.tabs(["Login", "Register", "Reset Password"])
    
    with tab1:
        render_login_form(supabase)
    
    with tab2:
        render_register_form(supabase)
    
    with tab3:
        render_reset_form(supabase)

def render_login_form(supabase: Client):
    """Render login form"""
    st.header("Login")
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="your@email.com")
        password = st.text_input("Password", type="password")
        
        submitted = st.form_submit_button("Login", type="primary", use_container_width=True)
        
        if submitted:
            if not email or not password:
                st.error("Please fill in all fields")
            elif not validate_email(email):
                st.error("Please enter a valid email address")
            else:
                success, message = login_user(supabase, email, password)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

def render_register_form(supabase: Client):
    """Render registration form"""
    st.header("Create Account")
    
    with st.form("register_form"):
        email = st.text_input("Email", placeholder="your@email.com")
        password = st.text_input("Password", type="password", 
                               help="Minimum 6 characters")
        password_confirm = st.text_input("Confirm Password", type="password")
        
        submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)
        
        if submitted:
            if not email or not password or not password_confirm:
                st.error("Please fill in all fields")
            elif not validate_email(email):
                st.error("Please enter a valid email address")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters long")
            elif password != password_confirm:
                st.error("Passwords do not match")
            else:
                success, message = register_user(supabase, email, password)
                if success:
                    st.success(message)
                    if st.session_state.authenticated:
                        st.rerun()
                else:
                    st.error(message)

def render_reset_form(supabase: Client):
    """Render password reset form"""
    st.header("Reset Password")
    st.info("Enter your email address and we'll send you a link to reset your password.")
    
    with st.form("reset_form"):
        email = st.text_input("Email", placeholder="your@email.com")
        
        submitted = st.form_submit_button("Send Reset Link", type="primary", use_container_width=True)
        
        if submitted:
            if not email:
                st.error("Please enter your email address")
            elif not validate_email(email):
                st.error("Please enter a valid email address")
            else:
                success, message = reset_password(supabase, email)
                if success:
                    st.success(message)
                else:
                    st.error(message)

def render_user_menu(supabase: Client):
    """Render user menu in sidebar when authenticated"""
    with st.sidebar:
        st.write(f"👤 **{st.session_state.user_email}**")
        
        if st.button("Logout", type="primary", use_container_width=True):
            logout(supabase)

# =====================================================
# MAIN APPLICATION WRAPPER
# =====================================================

def require_auth(supabase: Client):
    """Decorator-like function to require authentication"""
    # Check for existing session first
    if not st.session_state.get('authenticated', False):
        check_existing_session(supabase)
    
    # If still not authenticated, show auth form
    if not st.session_state.authenticated:
        render_auth_form(supabase)
        st.stop()
    else:
        # User is authenticated, show user menu
        render_user_menu(supabase)


def main():
    st.set_page_config(page_title="Kruscotto", page_icon="", layout="wide")
    # Replace your main() function with:

    supabase_client = init_supabase()
    init_session_state()
    require_auth(supabase_client)
    
    # User is guaranteed to be authenticated at this point
    user_id = st.session_state.user.id  # Use this for RLS queries
    # Initialize Supabase
    
    # Initialize session state
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
        # User is authenticated - show main application
        st.title(f"Welcome, {st.session_state.user['full_name']}!")
        
        # Sidebar with user info and logout
        # with st.sidebar:
        #     st.header("User Information")
        #     st.write(f"**Name:** {st.session_state.user['full_name']}")
        #     st.write(f"**Email:** {st.session_state.user['email']}")
        #     st.write(f"**User ID:** {st.session_state.user['id']}")
        #     
        #     if st.button("Logout", type="secondary"):
        #         logout_user()
        
        dashboard = st.Page("dashboard.py", title="Dashboard", icon=":material/search:")
        elenco_anagrafiche = st.Page("elenco_anagrafiche.py")
        casse = st.Page("casse.py")
        fatture = st.Page("fatture.py")
        altri_movimenti = st.Page("altri_movimenti.py")
        flussi_di_cassa = st.Page("flussi_di_cassa.py")
        feedback = st.Page("feedback.py")




        pg = st.navigation(
            {
            "Overview": [dashboard],
            "Anagrafiche": [elenco_anagrafiche],
            "Documenti": [casse, fatture, altri_movimenti],
            "Flussi di cassa": [flussi_di_cassa],
            "Comunicazioni": [feedback]
        }
        )
        pg.run()

        # # Main application content
        # st.header("Your Personal Dashboard")
        # 
        # # Load user-specific data
        # user_data = get_user_data(supabase_client, st.session_state.user['id'])
        # 
        # # Example: Display user data
        # if user_data:
        #     st.subheader("Your Data")
        #     for item in user_data:
        #         st.write(f"Data entry from {item.get('updated_at', 'Unknown')}")
        #         st.json(json.loads(item['data']))
        # else:
        #     st.info("No data found for your account.")
        # 
        # # Example: Form to save new data
        # st.subheader("Save New Data")
        # with st.form("save_data_form"):
        #     data_title = st.text_input("Title")
        #     data_content = st.text_area("Content")
        #     data_value = st.number_input("Value", value=0.0)
        #     
        #     if st.form_submit_button("Save Data"):
        #         if data_title and data_content:
        #             new_data = {
        #                 'title': data_title,
        #                 'content': data_content,
        #                 'value': data_value,
        #                 'timestamp': datetime.now().isoformat()
        #             }
        #             
        #             if save_user_data(supabase_client, st.session_state.user['id'], new_data):
        #                 st.success("Data saved successfully!")
        #                 st.rerun()
        #             else:
        #                 st.error("Failed to save data")
        #         else:
        #             st.error("Please fill in title and content")

if __name__ == "__main__":
    main()


