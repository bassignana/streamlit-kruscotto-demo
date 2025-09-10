"""

altri_movimenti_config = {
    'name_of_sql_column WITH PREFIX': {
        'data_type': it is, and will be, used for different pourposes.
                    - casting from and to query results into and to python datatypes, although not always necessary
                    - deciding what widget to show in forms
                    I don't like this coupling, but also I don't want to add too many fields in the below
                    config, and, at the same time, I don't want to do automatic type conversion.
                    I want to give them easy to understand names:
                    - string
                    - int: all integer number, STILL NOT USED IN THE PROJECT
                    - money: appropriate datatype for handling precision, ops and rounding
                    - date
                    I should not have any floating point number outside of money
                    - selectbox: HACK: unique datatype for creating a dropdown menu with options.
                        - movimenti_passivi_types
                        - movimenti_attivi_types
        'options': list of options to give to type selectbox
        'required': True, Required for both the table and forms, visualizations, etc...
        'placeholder': placeholder text that is displayed where you type values
        'help': text displayed when hovering over '?' symbol in some components
        'label': name on top of the input field.
    },
}
"""
from config import mp_tipo_options, ma_tipo_options

altri_movimenti_config = {

    'ma_numero': {
        'data_type': 'string',
        'required': True,
        'label': 'Numero Movimento Attivo',
        # 'placeholder': 'es. 2024-001',
        'help': 'Numero identificativo del movimento',
    },
    'ma_data': {
        'data_type': 'date',
        'required': True,
        'label': 'Data Movimento Attivo',
        'help': 'Data del movimento attivo',
    },
    'ma_importo_totale': {
        'data_type': 'money',
        'required': True,
        'label': 'Importo Totale Movimento',
        'help': 'Importo totale del movimento in Euro',
    },
    'ma_tipo': {
        'data_type': 'selectbox',
        'options': ma_tipo_options,
        'required': False,
        'label': 'Tipologia Movimento',
        'help': 'Categoria del movimento attivo',
    },
    'ma_cliente': {
        'data_type': 'string',
        'required': False,
        'label': 'Denominazione Cliente',
        'help': 'Denominazione del cliente',
    },



    'mp_numero': {
        'data_type': 'string',
        'required': True,
        'label': 'Numero Movimento Passivo',
        # 'placeholder': 'es. 2024-001',
        'help': 'Numero identificativo del movimento',
    },
    'mp_data': {
        'data_type': 'date',
        'required': True,
        'label': 'Data Movimento Passivo',
        'help': 'Data del movimento passivo',
    },
    'mp_importo_totale': {
        'data_type': 'money',
        'required': True,
        'label': 'Importo Totale Movimento',
        'help': 'Importo totale del movimento in Euro',
    },
    'mp_tipo': {
        'data_type': 'selectbox',
        'options': mp_tipo_options,
        'required': False,
        'label': 'Tipologia Movimento',
        'help': 'Categoria del movimento passivo',
    },
    'mp_fornitore': {
        'data_type': 'string',
        'required': False,
        'label': 'Denominazione Fornitore',
        'help': 'Denominazione del cliente',
    },



    'c_nome_cassa': {
        'data_type': 'string',
        'required': False,
        'label': 'Nome Cassa',
        'help': 'Nome della cassa',
    },
    'c_iban_cassa': {
        'data_type': 'string',
        'required': False,
        'label': 'Iban Cassa',
        'help': 'Eventuale IBAN associato alla cassa',
    },
    'c_descrizione_cassa': {
        'data_type': 'string',
        'required': False,
        'label': 'Descrizione Cassa',
        'help': 'Eventuale descrizione della cassa',
    },



}