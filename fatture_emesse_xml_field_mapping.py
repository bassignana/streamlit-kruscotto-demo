# Maps SQL table fields to XML tags and processing rules

XML_FIELD_MAPPING = {
    # Basic document information
    'invoice_number': {
        'xml_path': 'FatturaElettronicaBody/DatiGenerali/DatiGeneraliDocumento/Numero',
        'xml_tag': 'Numero',
        'data_type': 'string',
        'required': True,
        'section': 'body'
    },
    
    'document_date': {
        'xml_path': 'FatturaElettronicaBody/DatiGenerali/DatiGeneraliDocumento/Data',
        'xml_tag': 'Data',
        'data_type': 'date',
        'required': True,
        'section': 'body'
    },
    
    # 'currency': {
    #     'xml_path': 'FatturaElettronicaBody/DatiGenerali/DatiGeneraliDocumento/Divisa',
    #     'xml_tag': 'Divisa',
    #     'data_type': 'string',
    #     'required': False,
    #     'default': 'EUR',
    #     'section': 'body'
    # },
    
    # Financial amounts
    'total_amount': {
        'xml_path': 'FatturaElettronicaBody/DatiGenerali/DatiGeneraliDocumento/ImportoTotaleDocumento',
        'xml_tag': 'ImportoTotaleDocumento',
        'data_type': 'decimal',
        'required': True,
        'section': 'body'
    },
    
    # 'taxable_amount': {
    #     'xml_path': 'FatturaElettronicaBody/DatiBeniServizi/DatiRiepilogo/ImponibileImporto',
    #     'xml_tag': 'ImponibileImporto',
    #     'data_type': 'decimal',
    #     'required': False,
    #     'multiple': True,  # Can have multiple entries (sum them)
    #     'section': 'body'
    # },
    
    # 'vat_amount': {
    #     'xml_path': 'FatturaElettronicaBody/DatiBeniServizi/DatiRiepilogo/Imposta',
    #     'xml_tag': 'Imposta',
    #     'data_type': 'decimal',
    #     'required': False,
    #     'multiple': True,  # Can have multiple entries (sum them)
    #     'section': 'body'
    # },
    
    # 'withholding_amount': {
    #     'xml_path': 'FatturaElettronicaBody/DatiGenerali/DatiGeneraliDocumento/DatiRitenuta/ImportoRitenuta',
    #     'xml_tag': 'ImportoRitenuta',
    #     'data_type': 'decimal',
    #     'required': False,
    #     'section': 'body'
    # },
    
    # Payment information
    'due_date': {
        'xml_path': 'FatturaElettronicaBody/DatiPagamento/DettaglioPagamento/DataScadenzaPagamento',
        'xml_tag': 'DataScadenzaPagamento',
        'data_type': 'date',
        'required': False,
        'section': 'body'
    },
    
    # 'payment_method': {
    #     'xml_path': 'FatturaElettronicaBody/DatiPagamento/DettaglioPagamento/ModalitaPagamento',
    #     'xml_tag': 'ModalitaPagamento',
    #     'data_type': 'string',
    #     'required': False,
    #     'section': 'body'
    # },
    
    # 'iban': {
    #     'xml_path': 'FatturaElettronicaBody/DatiPagamento/DettaglioPagamento/IBAN',
    #     'xml_tag': 'IBAN',
    #     'data_type': 'string',
    #     'required': False,
    #     'section': 'body'
    # },
    
    # Supplier information (for determining client_supplier)
    # 'supplier_name_company': {
    #     'xml_path': 'FatturaElettronicaHeader/CedentePrestatore/DatiAnagrafici/Anagrafica/Denominazione',
    #     'xml_tag': 'Denominazione',
    #     'data_type': 'string',
    #     'required': False,
    #     'section': 'header',
    #     'parent_section': 'CedentePrestatore'
    # },
    
    # 'supplier_name_person_first': {
    #     'xml_path': 'FatturaElettronicaHeader/CedentePrestatore/DatiAnagrafici/Anagrafica/Nome',
    #     'xml_tag': 'Nome',
    #     'data_type': 'string',
    #     'required': False,
    #     'section': 'header',
    #     'parent_section': 'CedentePrestatore'
    # },
    
    # 'supplier_name_person_last': {
    #     'xml_path': 'FatturaElettronicaHeader/CedentePrestatore/DatiAnagrafici/Anagrafica/Cognome',
    #     'xml_tag': 'Cognome',
    #     'data_type': 'string',
    #     'required': False,
    #     'section': 'header',
    #     'parent_section': 'CedentePrestatore'
    # },
    
    # Customer information (for determining client_supplier)
    # 'customer_name_company': {
    #     'xml_path': 'FatturaElettronicaHeader/CessionarioCommittente/DatiAnagrafici/Anagrafica/Denominazione',
    #     'xml_tag': 'Denominazione',
    #     'data_type': 'string',
    #     'required': False,
    #     'section': 'header',
    #     'parent_section': 'CessionarioCommittente'
    # },
    
    # 'customer_name_person_first': {
    #     'xml_path': 'FatturaElettronicaHeader/CessionarioCommittente/DatiAnagrafici/Anagrafica/Nome',
    #     'xml_tag': 'Nome',
    #     'data_type': 'string',
    #     'required': False,
    #     'section': 'header',
    #     'parent_section': 'CessionarioCommittente'
    # },
    
    # 'customer_name_person_last': {
    #     'xml_path': 'FatturaElettronicaHeader/CessionarioCommittente/DatiAnagrafici/Anagrafica/Cognome',
    #     'xml_tag': 'Cognome',
    #     'data_type': 'string',
    #     'required': False,
    #     'section': 'header',
    #     'parent_section': 'CessionarioCommittente'
    # }
}