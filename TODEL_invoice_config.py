"""
Using full xml path, the first tag is not the root, but one of it immediate children.

todo: total amount -> 'xml_tag': 'ImportoTotaleDocumento' OR 'xml_tag': 'ImportoPagamento'

XML_FIELD_MAPPING = {
    'name_of_sql_column': {
        'xml_path': 'FatturaElettronicaBody/DatiGenerali/DatiGeneraliDocumento/Numero',
        'data_type': sql data type. I need to know what casting to apply to xml data.
                                    This should be the supabase types, like decimal, money, timestampz...
        'required': True, Required for both the table and forms, visualizations, etc...
        'placeholder': placeholed text that is displayed where you type values
        'help': text displayed when hovering over '?' symbol in some components
        'label': name on top of the input field.
    },
}
"""

XML_FIELD_MAPPING = {

    'id_codice': {
        'data_type': 'string',
        'required': True,
        'label': 'Id Codice',
        'placeholder': 'es. 09876543210',
        'help': 'Numero identificativo univoco del trasmittente',
        'xml_path': 'FatturaElettronicaHeader/DatiTrasmissione/IdTrasmittente/IdCodice'
    },
    'numero_fattura': {
        'data_type': 'string',
        'required': True,
        'label': 'Numero Fattura',
        'placeholder': 'es. 2024-001',
        'help': 'Numero identificativo della fattura',
        'xml_path': 'FatturaElettronicaBody/DatiGenerali/DatiGeneraliDocumento/Numero',
    },
    'data_documento': {
        'data_type': 'date',
        'required': True,
        'label': 'Data Documento',
        'help': 'Data di emissione della fattura',
        'xml_path': 'FatturaElettronicaBody/DatiGenerali/DatiGeneraliDocumento/Data'
    },
    'importo_totale_documento': {
        'data_type': 'money',
        'required': True,
        'label': 'Importo Totale',
        'help': 'Importo totale della fattura in Euro',
        'xml_path': 'FatturaElettronicaBody/DatiGenerali/DatiGeneraliDocumento/ImportoTotaleDocumento'
    },
    'data_scadenza_pagamento': {
        'data_type': 'date',
        'required': False,
        'label': 'Data Scadenza',
        'help': 'Data di scadenza del pagamento',
        'xml_path': 'FatturaElettronicaBody/DatiPagamento/DettaglioPagamento/DataScadenzaPagamento'
    },

}