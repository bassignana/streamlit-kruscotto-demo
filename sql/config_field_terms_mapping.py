"""
Configuration mapping for payment terms fields
Follows the same pattern as xml_mapping_emesse.py
"""

from datetime import date, timedelta

PAYMENT_TERMS_FIELD_MAPPING = {
    'due_date': {
        'label': 'Data Scadenza',
        'type': 'date',
        'required': True,
        'default': lambda: date.today() + timedelta(days=30),
        'help': 'Data di scadenza del pagamento'
    },
    'amount': {
        'label': 'Importo',
        'type': 'number',
        'required': True,
        'min_value': 0.01,
        'step': 0.01,
        'format': '%.2f',
        'help': 'Importo della scadenza in Euro'
    },
    'payment_method': {
        'label': 'Modalità di Pagamento',
        'type': 'selectbox',
        'required': True,
        'options': ['Bonifico', 'Contanti', 'Assegno', 'Carta di credito', 'RID', 'Altro'],
        'default': 'Bonifico',
        'help': 'Modalità di pagamento per questa scadenza'
    },
    'cash_account': {
        'label': 'Cassa/Conto',
        'type': 'selectbox',
        'required': True,
        'options': ['Banca Intesa', 'Cassa Contanti', 'Cassa Generica', 'INTESA SAN PAOLO'],
        'default': 'Banca Intesa',
        'help': 'Cassa o conto di destinazione del pagamento'
    },
    'notes': {
        'label': 'Note',
        'type': 'text_area',
        'required': False,
        'max_chars': 500,
        'help': 'Note aggiuntive per questa scadenza (opzionale)'
    },
    'is_paid': {
        'label': 'Pagato',
        'type': 'checkbox',
        'required': False,
        'default': False,
        'help': 'Segna come pagato se il pagamento è stato effettuato'
    },
    'payment_date': {
        'label': 'Data Pagamento',
        'type': 'date',
        'required': False,
        'help': 'Data in cui il pagamento è stato effettuato (solo se pagato)'
    }
}

# Field groups for better organization in forms
PAYMENT_TERMS_FIELD_GROUPS = {
    'basic_info': {
        'label': 'Informazioni Base',
        'fields': ['due_date', 'amount', 'payment_method', 'cash_account']
    },
    'additional_info': {
        'label': 'Informazioni Aggiuntive',
        'fields': ['notes']
    },
    'payment_status': {
        'label': 'Stato Pagamento',
        'fields': ['is_paid', 'payment_date']
    }
}

# Validation rules
VALIDATION_RULES = {
    'amount_positive': {
        'field': 'amount',
        'rule': lambda x: x > 0,
        'message': 'L\'importo deve essere maggiore di zero'
    },
    'payment_date_if_paid': {
        'fields': ['is_paid', 'payment_date'],
        'rule': lambda is_paid, payment_date: not is_paid or payment_date is not None,
        'message': 'La data di pagamento è richiesta se il pagamento è marcato come effettuato'
    },
    'payment_date_not_future': {
        'field': 'payment_date',
        'rule': lambda x: x is None or x <= date.today(),
        'message': 'La data di pagamento non può essere nel futuro'
    }
}