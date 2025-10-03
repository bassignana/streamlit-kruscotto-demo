"""
File for storing functions to test that don't depend on shared state,
so that I can import them without errors when I run pytest.
"""
import re
error = str

def get_cleaned_company_identifiers(codice_fiscale: str, partita_iva: str) -> tuple[error, str, str]:
    """
    CF pattern breakdown
    exactly 6 letters: [a-zA-Z]{6}
    exactly 2 numbers: \d{2}
    ...
    """
    cf_pattern = r"[a-zA-Z]{6}\d{2}[a-zA-Z]{1}\d{2}[a-zA-Z]{1}\d{3}[a-zA-Z]{1}"
    eleven_numbers_pattern = r"\d{11}"
    error_message = ''

    cf_clean = codice_fiscale.strip().upper()
    piva_clean = partita_iva.strip()

    if not all([cf_clean, piva_clean]):
        error_message = "Inserire tutti i campi obbligatori"

    elif not (re.fullmatch(cf_pattern, cf_clean) or
            re.fullmatch(eleven_numbers_pattern, cf_clean)):
        error_message = "La struttura del Codice Fiscale non è corretta"

    elif not re.fullmatch(eleven_numbers_pattern, piva_clean):
        error_message = "La Partita IVA deve essere composta da 11 numeri"

    return error_message, cf_clean, piva_clean

