"""
Creates intermediate records SPECIDICALLY FOR INSERTING SCADENZE AND FATTURE,
with or without terms,
mapping xml processed data to PREFIXED sql table field names.

It will produce data of the form:
TABLE_PREFIX_extracted_name: value, where TABLE_PREFIX is unique for each table
and extracted_name is the input field name.
All fields that match TABLE_PREFIX_extracted_name for a specified TABLE_PREFIX will be
extracted in the intermediate record.

IN THEORY, this COULD BE a standalone operation that I think can be done regardless of business logic.
Augmenting the record with fields like user_id should be a responsibility of the front end.
I could refactor this when I have more time, for not it will stay.
Mainly, the refactoring should be centered around creating functions like get_emesse_record()
where it does all the logic of understanding if there are terms or not. If I had more table with the
same logic, I would automate this also further.

SQL LOGIC DEPENDENCY
There is a strong logic dependency on how the sql file is structured and what fields have the
prefix. Not ideal but for now will do.

NOTE: for parsing table definitions I don't use grep because I don't want
      another dependency to track on the server.
      Also if I don't have to manage any tmp file is better.

GOOD: Augmenting the input data structure with new fields

Here I do NO CONVERSION, still all values in strings or none, or list.

# NOTE: for null fields is better to use the default NULL in the
#       database so the query are easier to do since NULL is valid for
#       any datatype.

IF the distinction between this file and invoice_db_insert.py is correct, then if I change logic
in this file about what records gets inserted and other business rules, then the invoice_db_insert.py
should not need to change, except for a couple of error messages if they have to be tailored and the RPC
function.
"""

import os
import glob
import pprint
from invoice_xml_processor import process_xml_list

def extract_fields_name(sql_file_path = 'sql/02_create_tables.sql', prefix='fe_'):
    field_names = []
    with open(sql_file_path, 'r') as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith(prefix):
                # Get first word (field name)
                field_name = stripped.split()[0]
                # Remove prefix because I have to check against field names in
                # the xml_fields which has names without prefix.
                field_name = field_name[len(prefix):]
                field_names.append(field_name)
    return field_names

def extract_xml_records(parsing_results, partita_iva_azienda) -> list[dict]:
    results = []

    for xml in parsing_results:
        # Copy because I'll pop() some fields, but I want to keep the
        # original referenced datat in the result object intact.
        xml_data = xml['data'].copy()
        record_to_insert = {}
        terms_to_insert = []

        result = {
            'filename': xml['filename'],
            'data': xml['data'],
            'status': xml['status'],
            'error_message': xml['error_message'],
            'record': record_to_insert,
            'terms': terms_to_insert,
            'invoice_type': 'unknown'
        }

        if result['status'] == 'error':
            results.append(result)
            continue # to the next file since this one is already errored

        term_type = 'unknown'
        xml_term_value = xml_data.get('data_scadenza_pagamento', None)
        if isinstance(xml_term_value, str):
            term_type = 'single_payment'
        elif isinstance(xml_term_value, list):
            term_type = 'multiple_payments'
        elif xml_term_value is None:
            term_type = 'no_term' # TODO; I have yet to implement this case
        if term_type == 'unknown':
            result['status'] = 'error'
            result['error_message'] = result['error_message'] + f'RECORD CREATION: xml_term_value {type(xml_term_value)} does not match desired types.'
            results.append(result)
            continue # to the next file

        invoice_type = 'unknown'
        if xml_data['partita_iva_prestatore'] == partita_iva_azienda:
            invoice_type = 'emessa'
            result['invoice_type'] = invoice_type
        elif xml_data.get('partita_iva_committente',None):
            if xml_data['partita_iva_committente'] == partita_iva_azienda:
                invoice_type = 'ricevuta'
                result['invoice_type'] = invoice_type
        if invoice_type == 'unknown':
            result['status'] = 'error'
            result['error_message'] = result['error_message'] + f"RECORD CREATION: La fattura {xml['filename']} non riguarda la partita IVA {partita_iva_azienda}"
            results.append(result)
            continue # to the next xml file

        if invoice_type == 'emessa' and term_type != 'multiple_payments':

            # VERY IMPORTANT LOGIC: While fields_to_insert will generate
            # the full spectrum of insertable fields, only fields present in
            # the parsed xml data will be inserted.
            #
            # This means that I can add any field that I want to table, and if
            # they are not present, they will be skipped in this step, so that I
            # can value them later or leave them to their default or managing them
            # with functions and triggers.
            #
            # Here it's important to not get confused with the fact that I can add
            # any random field in a table, even with the prefix, and as long as its
            # name is not equal to a field present in the xml file, I can manage it
            # later. The prefix is more for creating unique names that are easy to find
            # and replace in the iteration phase.
            fields_to_insert = extract_fields_name(prefix='fe_')
            for (sql_field, value) in xml_data.items():
                if sql_field in fields_to_insert:
                    record_to_insert['fe_' + sql_field] = value

            # record_to_insert['user_id'] = st.session_state.user.id should go in the front end logic,
            # especially because it is dependent on state.
            # It can also be appended automatically with store procedures or triggers, so I don't have to
            # do it manually.

            results.append(result)

        elif invoice_type == 'ricevuta' and term_type != 'multiple_payments':
            fields_to_insert = extract_fields_name(prefix='fr_')
            for (sql_field, value) in xml_data.items():
                if sql_field in fields_to_insert:
                    record_to_insert['fr_' + sql_field] = value
            results.append(result)

        elif invoice_type == 'emessa' and term_type == 'multiple_payments':

            # All the popped fields are all the fields that are a list
            # when parsing an XML with multiple terms.
            #
            # Here I'm assuming that data_scadenza_pagamento and importo_pagamento_rata
            # need to be present, otherwise I'll get a key error,
            # while iban_cassa and nome_cassa can be not present in the invoice.
            terms_due_date =  xml_data.pop('data_scadenza_pagamento')
            terms_amount =  xml_data.pop('importo_pagamento_rata')

            # All fields in the extracted records will always be present,
            # at least with a None value, since I force this in invoice_invoice_xml_processor.py .
            # The default None is just to be sure in case of massive changes to the codebase.
            terms_iban =  xml_data.pop('iban_cassa', None)
            if not terms_iban:
                terms_iban = [None]*len(terms_due_date)
            terms_cassa =  xml_data.pop('nome_cassa', None)
            if not terms_cassa:
                terms_cassa = [None]*len(terms_due_date)

            # By popping data_scadenza_pagamento first,
            # I'm ensuring that data_scadenza_pagamento will be NULL
            # in the database when there are terms.
            fields_to_insert = extract_fields_name(prefix='fe_')
            for (sql_field, value) in xml_data.items():
                if sql_field in fields_to_insert:
                    record_to_insert['fe_' + sql_field] = value

            fields_to_insert = extract_fields_name(prefix='rfe_')
            for i in range(len(terms_due_date)):
                term_record = {}
                for (sql_field, value) in xml_data.items():
                    if sql_field in fields_to_insert:
                        term_record['rfe_' + sql_field] = value
                term_record['rfe_' + 'data_scadenza_pagamento'] = terms_due_date[i]
                term_record['rfe_' + 'importo_pagamento_rata'] = terms_amount[i]
                term_record['rfe_' + 'iban_cassa'] = terms_iban[i]
                term_record['rfe_' + 'nome_cassa'] = terms_cassa[i]
                terms_to_insert.append(term_record)

            results.append(result)

        elif invoice_type == 'ricevuta' and term_type == 'multiple_payments':

            terms_due_date =  xml_data.pop('data_scadenza_pagamento')
            terms_amount =  xml_data.pop('importo_pagamento_rata')
            terms_iban =  xml_data.pop('iban_cassa', None)
            if not terms_iban:
                terms_iban = [None]*len(terms_due_date)
            terms_cassa =  xml_data.pop('nome_cassa', None)
            if not terms_cassa:
                terms_cassa = [None]*len(terms_due_date)

            fields_to_insert = extract_fields_name(prefix='fr_')
            for (sql_field, value) in xml_data.items():
                if sql_field in fields_to_insert:
                    record_to_insert['fr_' + sql_field] = value

            fields_to_insert = extract_fields_name(prefix='rfr_')
            for i in range(len(terms_due_date)):
                term_record = {}
                for (sql_field, value) in xml_data.items():
                    if sql_field in fields_to_insert:
                        term_record['rfr_' + sql_field] = value
                term_record['rfr_' + 'data_scadenza_pagamento'] = terms_due_date[i]
                term_record['rfr_' + 'importo_pagamento_rata'] = terms_amount[i]
                term_record['rfr_' + 'iban_cassa'] = terms_iban[i]
                term_record['rfr_' + 'nome_cassa'] = terms_cassa[i]
                terms_to_insert.append(term_record)

            results.append(result)

        else:
            result['status'] = 'error'
            result['error_message'] = result['error_message'] + f"RECORD CREATION: Unknown case."
            results.append(result)
            continue # to the next xml file

    return results

if __name__ == '__main__':
    partita_iva_azienda = '04228480408'
    xml_files = glob.glob(os.path.join('fe_scadenze_multiple/', "*.xml"))
    parsing_results, error = process_xml_list(xml_files)
    results = extract_xml_records(parsing_results, partita_iva_azienda)

    for r in results:
        pprint.pprint(r)
    print('\n\n\n\n')
    for r in results:
        print(r['filename'])
        print(r['error_message'])
