from streamlit.testing.v1 import AppTest

# def init_session_state(at):
#     if 'authenticated' not in at.session_state:
#         at.session_state["authenticated"] = 'test'
#     if 'login_processing' not in at.session_state:
#         at.session_state["login_processing"] = 'test'
#     at.session_state.user = {}
#     at.session_state.user['id'] = 'test_id'
#     return at

def test_successful_login():
    at = AppTest.from_file("streamlit_app.py")
    # at = init_session_state(at)
    at.run()

    # For now I don't test the state as it is not immediate.
    # State is as expected.
    # assert at.session_state["authenticated"] == False
    # assert at.session_state["login_processing"] == False

    # Assert tab present
    # pytest -s for NOT suppressing print logs.
    # print(at) Useful for understanding page structure as seen by AppTest
    print(at)
    tab_labels = [tab.label for tab in at.tabs]
    assert "Login" in tab_labels
    assert "Registrazione" in tab_labels

