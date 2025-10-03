import pytest
from anagrafica_utils import get_cleaned_company_identifiers

# Not used?
@pytest.fixture
def valid_cf_piva():
    return {
        "cf"  : "RSSMRA85M01H501Z",  # valid CF pattern
        "piva": "12345678900"  # 11 digits
    }


# @formatter:off
@pytest.mark.parametrize(
    "cf_input, piva_input, expected_error",
    [
        ("RSSMRA85M01H501Z", "12345678901", ""),                                                # P: both valid
        ("rssmra85m01h501z", "12345678901", ""),                                                # P: lowercase CF, should be uppercased
        ("12345678901", "12345678901", ""),                                                     # P: CF with 11 digits is allowed
        ("RSSMRA85M01H501", "12345678901", "La struttura del Codice Fiscale non è corretta"),   # F: CF too short
        ("RSSMRA85M01H501Z", "1234567890", "La Partita IVA deve essere composta da 11 numeri"), # F: PIVA too short
        ("", "", "Inserire tutti i campi obbligatori"),                                         # F: missing both
        ("    ", "    ", "Inserire tutti i campi obbligatori"),                                 # F: whitespace only
        ("INVALIDCF123", "INVALIDPIVA", "La struttura del Codice Fiscale non è corretta"),      # F: bad formats
        ("RSSMRA85M01H501Z", "", "Inserire tutti i campi obbligatori"),                         # F: missing PIVA
        ("", "12345678901", "Inserire tutti i campi obbligatori")                               # F: missing CF
    ]
# @formatter:on
)
def test_get_cleaned_company_identifiers(cf_input, piva_input, expected_error):
    error, cleaned_cf, cleaned_piva = get_cleaned_company_identifiers(cf_input, piva_input)

    assert error == expected_error

    if expected_error == "":
        assert cleaned_cf == cf_input.strip().upper()
        assert cleaned_piva == piva_input.strip()
