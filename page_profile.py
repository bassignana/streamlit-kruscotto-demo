import streamlit as st
from utils import setup_page

def main():
    user_id, supabase_client, page_can_render = setup_page("Anagrafica Azienda")
    if page_can_render:
        st.text_input('Email:',
                      value = st.session_state.user.user_metadata['email'],
                      disabled = True,
                      width = 300)

        if st.button('Logout', type='primary'):
            supabase_client.auth.sign_out()
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()