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

def main():
    st.set_page_config(page_title="Kruscotto", page_icon="", layout="wide")
    
    # Initialize Supabase
    supabase_client = init_supabase()
    
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


