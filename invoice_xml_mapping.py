"""
Using full xml path, the first tag is not the root, but one of it immediate children.

In generale, il campo della fattura elettronica
FatturaElettronicaHeader/CedentePrestatore/DatiAnagrafici/IdFiscaleIVA/IdCodice
deve essere obbligatoriamente valorizzato con il valore della partita IVA, attraverso la quale
posso verificare che si tratta di una fattura emessa.
Infatti mi aspetto che un Prestatore d'opera debba sempre avere P IVA, a differenza del committente.


Casistiche: (gestite in invoice_record_creation.py)
Se sono Cedente/Prestatore -> EMESSE:
- Le informazioni del committente che estraggo sono le seguenti, per ora.
-- FatturaElettronicaHeader/CessionarioCommittente/DatiAnagrafici/IdFiscaleIVA/IdCodice
   campo obbligatorio SOLO nel caso in cui il CessionarioCommittente sia titolare di partita IVA
-- FatturaElettronicaHeader/CessionarioCommittente/DatiAnagrafici/CodiceFiscale
   campo NON obbligatorio, valorizzato con il CF del Committente. Dai documenti non e' obbligatorio.
-- FatturaElettronicaHeader/CessionarioCommittente/DatiAnagrafici/Anagrafica/Denominazione
   in caso di soggetto giuridico titolare di partita IVA
-- FatturaElettronicaHeader/CessionarioCommittente/DatiAnagrafici/Anagrafica/Nome
-- FatturaElettronicaHeader/CessionarioCommittente/DatiAnagrafici/Anagrafica/Cognome
   in caso di soggetti con CF

Se sono CessionarioCommittente -> RICEVUTE:
- Il campo della fattura elettronica FatturaElettronicaHeader/CedentePrestatore/DatiAnagrafici/IdFiscaleIVA/IdCodice
  potrebbe non essere valorizzato.
- Le informazioni del prestatore che estraggo sono le seguenti, per ora.
-- FatturaElettronicaHeader/CedentePrestatore/DatiAnagrafici/IdFiscaleIVA/IdCodice: partita IVA prestatore
-- FatturaElettronicaHeader/CedentePrestatore/DatiAnagrafici/Anagrafica/Denominazione

Per le scadenze dei pagamenti:
per emesse e per ricevute indistintamente
- se la fattura ha FatturaElettronicaBody/DatiPagamento/DettaglioPagamento/DataScadenzaPagamento
  allora uso quella come unica rata
- se la fattura ha piu' rate impostate nell'xml, uso quelle come scadenze.
  In particolare, 0, 1 o piu' righe contenenti le seguenti informazioni possono
  essere presenti:
-- FatturaElettronicaBody/DatiPagamento/DettaglioPagamento/DataRiferimentoTerminiPagamento
   e' la data da cui decorrono X giorni per la scadenza, dati da
-- FatturaElettronicaBody/DatiPagamento/DettaglioPagamento/GiorniTerminiPagamento
   che dovrebbe corrispondere al campo, gia' calcolato
-- FatturaElettronicaBody/DatiPagamento/DettaglioPagamento/DataScadenzaPagamento
  per individuare il conto del beneficiario posso servirmi dei campi
-- FatturaElettronicaBody/DatiPagamento/DettaglioPagamento/ImportoPagamento e' l'importo della rata
-- FatturaElettronicaBody/DatiPagamento/DettaglioPagamento/IstitutoFinanziario
-- FatturaElettronicaBody/DatiPagamento/DettaglioPagamento/IBAN
- se la fattura non ha nulla di cui sopra, uso un default alla fine di X=1 mesi dopo.

Per le casse:
solo per le fatture emesse, di cui io sono il beneficiario,
FatturaElettronicaBody/DatiPagamento/DettaglioPagamento/IBAN NON OBBLIGATORIO
altrimenti: "non specificata"

XML_FIELD_MAPPING = {
    'name_of_sql_column without prefix': {
        'xml_path': 'FatturaElettronicaBody/DatiGenerali/DatiGeneraliDocumento/Numero',
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
        
        'required': True, Required for both the table and forms, visualizations, etc...
        'placeholder': placeholder text that is displayed where you type values
        'help': text displayed when hovering over '?' symbol in some components
        'label': name on top of the input field.
    },
}
"""

XML_FIELD_MAPPING = {

    # Field required in all invoices.
    'numero_fattura': {
        'data_type': 'string',
        'required': True,
        'label': 'Numero Fattura',
        # 'placeholder': 'es. 2024-001',
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

    # partita iva dtype: string because with int is not easy to deal with trailing 0s.
    'partita_iva_prestatore': {
        'data_type': 'string',
        'required': True,
        'label': 'P. IVA Prestatore',
        # 'placeholder': 'es. 09876543210',
        'help': 'Partita IVA del Prestatore',
        'xml_path': 'FatturaElettronicaHeader/CedentePrestatore/DatiAnagrafici/IdFiscaleIVA/IdCodice'
    },

    # Not required fields in all invoices

    # Can be present more than one time in case of multiple terms.
    # In the rate_* tables, this field is called data_scadenza_pagamento
    # todo: WHY THIS DIFFERENCE IN NAME? I've changed it but check that everything is correct.
    'data_scadenza_pagamento': {
        'data_type': 'date',
        'required': False,
        'label': 'Data Scadenza',
        'help': 'Data di scadenza del pagamento',
        'xml_path': 'FatturaElettronicaBody/DatiPagamento/DettaglioPagamento/DataScadenzaPagamento'
    },

    # Can be present more than one time in case of multiple terms.
    'importo_pagamento_rata': {
        'data_type': 'money',
        'required': False,
        'label': 'Importo Rata',
        'help': 'Importo della rata',
        'xml_path': 'FatturaElettronicaBody/DatiPagamento/DettaglioPagamento/ImportoPagamento'
    },

    # Not required fields to parse only for Emesse
    'partita_iva_committente': {
        'data_type': 'string',
        'required': False,
        'label': 'P. IVA Committente',
        # 'placeholder': 'es. 09876543210',
        'help': 'Partita IVA del Committente',
        'xml_path': 'FatturaElettronicaHeader/CessionarioCommittente/DatiAnagrafici/IdFiscaleIVA/IdCodice'
    },

    'codice_fiscale_committente': {
        'data_type': 'string',
        'required': False,
        'label': 'CF Committente',
        # 'placeholder': 'es. BSSTMS96T27B885E',
        'help': 'Codice Fiscale del Committente',
        'xml_path': 'FatturaElettronicaHeader/CessionarioCommittente/DatiAnagrafici/CodiceFiscale'
    },

    'denominazione_committente': {
        'data_type': 'string',
        'required': False,
        'label': 'Denominazione Committente',
        # 'placeholder': 'Ditta ACME Srl',
        'help': 'Denominazione del soggetto giuridico committente',
        'xml_path': 'FatturaElettronicaHeader/CessionarioCommittente/DatiAnagrafici/Anagrafica/Denominazione'
    },

    'nome_committente': {
        'data_type': 'string',
        'required': False,
        'label': 'Nome Committente',
        # 'placeholder': 'Mario',
        'help': 'Nome del committente',
        'xml_path': 'FatturaElettronicaHeader/CessionarioCommittente/DatiAnagrafici/Anagrafica/Nome'
    },

    'cognome_committente': {
        'data_type': 'string',
        'required': False,
        'label': 'Cognome Committente',
        # 'placeholder': 'Rossi',
        'help': 'Cognome del committente',
        'xml_path': 'FatturaElettronicaHeader/CessionarioCommittente/DatiAnagrafici/Anagrafica/Cognome'
    },

    'nome_cassa': {
        'data_type': 'string',
        'required': False,
        'label': "Cassa",
        'help': "Nome dell'istituto del beneficiario",
        'xml_path': 'FatturaElettronicaBody/DatiPagamento/DettaglioPagamento/IstitutoFinanziario'
    },

    'iban_cassa': {
        'data_type': 'string',
        'required': False,
        'label': "IBAN",
        'help': "IBAN associato alla cassa",
        'xml_path': 'FatturaElettronicaBody/DatiPagamento/DettaglioPagamento/IBAN'
    },

    # Not required fields to parse only for Ricevute
    'denominazione_prestatore': {
        'data_type': 'string',
        'required': False,
        'label': 'Denominazione Prestatore',
        # 'placeholder': 'Ditta ACME Srl',
        'help': 'Denominazione del soggetto giuridico prestatore',
        'xml_path': 'FatturaElettronicaHeader/CedentePrestatore/DatiAnagrafici/Anagrafica/Denominazione'
    },

}