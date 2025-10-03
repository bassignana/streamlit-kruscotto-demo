from streamlit.testing.v1 import AppTest
import streamlit as st
import pytest

def test_incorrect_password():
    at = AppTest.from_file("streamlit_app.py").run()

    # Testing is agnostic to whether elements are in a form or not with regard to selection.
    at.text_input[0].input("test3@gmail.com")
    at.text_input[1].input("wrong_pwd")
    at.button[0].click()

    at.run()
    assert "Credenziali di accesso non valide" in at.error[0].value

def test_correct_password():
    at = AppTest.from_file("streamlit_app.py").run()

    # Testing is agnostic to whether elements are in a form or not with regard to selection.
    at.text_input[0].input("test3@gmail.com")
    at.text_input[1].input(st.secrets["test_password"])
    at.button[0].click()
    at.run()

    # Note that I can inspec session_state with print(at).
    # print(at)

    assert len(at.error) == 0


# @formatter:off
@pytest.mark.parametrize(
    "cf_input, piva_input, expected_error",
    [
        ("rssmra85m01h501z", "12345678900", ""),                                                # P: lowercase CF, should be uppercased
        ("12345678901", "12345678901", ""),                                                     # P: CF with 11 digits is allowed
        ("RSSMRA85M01H501", "12345678901", "La struttura del Codice Fiscale non è corretta"),   # F: CF too short
        ("RSSMRA85M01H501Z", "1234567890", "La Partita IVA deve essere composta da 11 numeri"), # F: PIVA too short
        ("", "", "Inserire tutti i campi obbligatori"),                                         # F: missing both
        ("    ", "    ", "Inserire tutti i campi obbligatori"),                                 # F: whitespace only
        ("INVALIDCF123", "INVALIDPIVA", "La struttura del Codice Fiscale non è corretta"),      # F: bad formats
        ("RSSMRA85M01H501Z", "", "Inserire tutti i campi obbligatori"),                         # F: missing PIVA
        ("", "12345678901", "Inserire tutti i campi obbligatori"),                              # F: missing CF
        ("RSSMRA85M01H501Z", "12345678900", "")                                                 # P: both valid
        # Restore default.
    ]
    # @formatter:on
)
def test_navigation(cf_input, piva_input, expected_error):
    at = AppTest.from_file("streamlit_app.py").run()

    at.text_input[0].input("test3@gmail.com")
    at.text_input[1].input(st.secrets["test_password"])
    at.button[0].click()
    at.run()

    at.switch_page("page_anagrafica_azienda.py").run()
    at.text_input[0].input(cf_input)
    at.text_input[1].input(piva_input)
    at.button[0].click()
    at.run()


    if not expected_error:
        # TODO: what is the correct way of testing that there are no errors in the page?
        #  assert not 'error' in at does not work correctly I think.
        assert len(at.error) == 0
    else:
        assert at.error[0].value == expected_error
        assert len(at.error) == 1
