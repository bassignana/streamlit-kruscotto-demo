import os
import streamlit as st

def get_pages_paths():

    excluded_files = ['__init__.py', 'streamlit_pages_generator.py', '__pycache__' ]
    files = os.listdir(path='streamlit_pages/')
    pages = [f'streamlit_pages/{f}' for f in files if f not in excluded_files]
    return pages

def get_navigation_obj():
    
    pages = get_pages_paths()
    pg = st.navigation(
            {"Example Section": [st.Page(f"{page}") for page in pages]}
        )

    return pg

# Old behaviour for reference:

        # dashboard = st.Page("dashboard.py", title="Dashboard", icon=":material/search:")
        # #elenco_anagrafiche = st.Page("elenco_anagrafiche.py")
        # casse = st.Page("casse.py")
        # fatture = st.Page("fatture.py")
        # #altri_movimenti = st.Page("altri_movimenti.py")
        # #flussi_di_cassa = st.Page("flussi_di_cassa.py")
        # feedback = st.Page("feedback.py")
        # page_test = st.Page("streamlit_pages/p_test.py")

        # pg = st.navigation(
        #     {
        #     "Overview": [dashboard],
        #     #"Anagrafiche": [elenco_anagrafiche],
        #     "Documenti": [casse, fatture],
        #     #"Flussi di cassa": [flussi_di_cassa],
        #     "Comunicazioni": [feedback, page_test]
        # }
        # )
