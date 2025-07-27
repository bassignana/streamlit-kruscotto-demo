# Maps SQL table fields to XML tags and processing rules

"""
For now, I don't even know if xml_path is useful.

XML_FIELD_MAPPING = {
    'name_of_sql_column': {
        'xml_path': 'FatturaElettronicaBody/DatiGenerali/DatiGeneraliDocumento/Numero',
        'sql_data_type': 'string', I need to know what casting to apply to xml data.
                                    This should be the supabase types, like decimal, money, timestampz...
        'required': True, Required for both the table and forms, visualizations, etc...
    },
}
"""

XML_FIELD_MAPPING = {
    'invoice_number': {
        'xml_tag': 'Numero',
        'sql_data_type': 'integer',
        'required': True,
    },
}