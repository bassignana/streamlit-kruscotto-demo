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

IF the distinction between this file and local_invoice_uploader.py is correct, then if I change logic
in this file about what records gets inserted and other business rules, then the local_invoice_uploader.py
should not need to change, except for a couple of error messages if they have to be tailored and the RPC
function.
"""

import os
import glob
import pprint
from dateutil.relativedelta import relativedelta
from datetime import datetime
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

def get_logicless_field_in_list(xml_data, field_name:str, len_field:list[str | None]) -> list[str | None]:
    field = xml_data.pop(field_name, None)
    if field is None:
        field = [None]*len(len_field)
    elif isinstance(field, str):
        field = [field]
    elif isinstance(field, list):
        pass
    else:
        raise Exception("Error in simple validation.")

    return field

def extract_xml_records(parsing_results, partita_iva_azienda) -> list[dict]:
    MONTHS_IN_ADVANCE = 1 # TODO: factor out
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
            term_type = 'no_term'
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

        # if invoice_type == 'emessa' and term_type != 'multiple_payments':
        if invoice_type == 'emessa':

            # Since I'm going to append into the record, I want values in a list always

            # TODO; I'm not sure that importo_pagamento_rata is always valued,
            #  and also that data_scadenza_pagamento is the only field needed for
            #  understanding if an invoice has no terms.
            terms_due_date =  xml_data.pop('data_scadenza_pagamento', None)
            if isinstance(terms_due_date, list):
                assert term_type == 'multiple_payments', f"terms_due_date - term type: expected multiple_payments, got {term_type}"

            elif isinstance(terms_due_date, str):
                assert term_type == 'single_payment', f"terms_due_date - term type: expected single_payment, got {term_type}"
                # Be sure to not do list('string') otherwise ['s' 't' 'r' 'i' 'n' 'g']
                terms_due_date = [terms_due_date]

            elif terms_due_date is None:
                assert term_type == 'no_term', f"terms_due_date - term type: expected no_term, got {term_type}"
                data_documento = xml_data.get('data_documento')
                assert data_documento is not None, "data_documento can't be None."

                data_documento_date = datetime.fromisoformat(data_documento)
                first_day = datetime(data_documento_date.year, data_documento_date.month, 1)
                last_day_next_X_months = first_day + relativedelta(months=MONTHS_IN_ADVANCE + 1, days=-1)
                terms_due_date = [last_day_next_X_months.date().isoformat()]

            else:
                assert False, f"Branching error for terms_due_date."


            # terms_amount does not respond to the same types of logic data_scadenza_pagamento:
            # for example data_scadenza_pagamento can be None but importo_pagamento_rata can be valued
            # with a single value. I cannot then do the assert-kind-of-checks that I do above.
            terms_amount =  xml_data.pop('importo_pagamento_rata')
            if isinstance(terms_amount, list):
                pass

            elif isinstance(terms_amount, str):
                terms_amount = [terms_amount]

            elif terms_amount is None:
                total_amount = xml_data.get('importo_totale_documento')
                terms_amount = [total_amount]

            else:
                assert False, "Branching error for terms_amount."


            terms_iban = get_logicless_field_in_list(xml_data, 'iban_cassa', terms_due_date)
            terms_cassa = get_logicless_field_in_list(xml_data,'nome_cassa', terms_due_date)

            assert (len(terms_due_date) == len(terms_amount) == len(terms_iban) == len(terms_cassa)), "Terms fields' len() does not match."




            # TODO; at this point, I might not need to differenciate between single and
            #  multiple payments terms, because the logic is the same: if there is no term,
            #  create an appropriate terms_due_date, else insert all the terms extracted.
            # assert len(terms_due_date) == 1, "Expected len == 1 in != 'multiple_payments' case."
            # assert len(terms_amount) == 1, "Expected len == 1 in != 'multiple_payments' case."
            # assert len(terms_iban) == 1, "Expected len == 1 in != 'multiple_payments' case."
            # assert len(terms_cassa) == 1, "Expected len == 1 in != 'multiple_payments' case."

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
        elif invoice_type == 'ricevuta':

            terms_due_date =  xml_data.pop('data_scadenza_pagamento', None)
            if isinstance(terms_due_date, list):
                assert term_type == 'multiple_payments', f"RICEVUTA terms_due_date - term type: expected multiple_payments, got {term_type}"

            elif isinstance(terms_due_date, str):
                assert term_type == 'single_payment', f"RICEVUTA terms_due_date - term type: expected single_payment, got {term_type}"
                terms_due_date = [terms_due_date]

            elif terms_due_date is None:
                assert term_type == 'no_term', f"RICEVUTA terms_due_date - term type: expected no_term, got {term_type}"
                data_documento = xml_data.get('data_documento')
                assert data_documento is not None, "data_documento can't be None."

                data_documento_date = datetime.fromisoformat(data_documento)
                first_day = datetime(data_documento_date.year, data_documento_date.month, 1)
                last_day_next_X_months = first_day + relativedelta(months=MONTHS_IN_ADVANCE + 1, days=-1)
                terms_due_date = [last_day_next_X_months.date().isoformat()]

            else:
                assert False, f"RICEVUTA Branching error for terms_due_date."


            terms_amount =  xml_data.pop('importo_pagamento_rata')
            if isinstance(terms_amount, list):
                pass

            elif isinstance(terms_amount, str):
                terms_amount = [terms_amount]

            elif terms_amount is None:
                total_amount = xml_data.get('importo_totale_documento')
                terms_amount = [total_amount]

            else:
                assert False, "RICEVUTA Branching error for terms_amount."


            terms_iban = get_logicless_field_in_list(xml_data,'iban_cassa', terms_due_date)
            terms_cassa = get_logicless_field_in_list(xml_data,'nome_cassa', terms_due_date)

            assert (len(terms_due_date) == len(terms_amount) == len(terms_iban) == len(terms_cassa)), "RICEVUTA Terms fields' len() does not match."

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
        # OLD VERSION COMMENTING ALL OUT FOR TESTING
        # elif invoice_type == 'ricevuta' and term_type != 'multiple_payments':
        #     fields_to_insert = extract_fields_name(prefix='fr_')
        #     for (sql_field, value) in xml_data.items():
        #         if sql_field in fields_to_insert:
        #             record_to_insert['fr_' + sql_field] = value
        #     results.append(result)
        #
        # elif invoice_type == 'emessa' and term_type == 'multiple_payments':
        #
        #     # All the popped fields are all the fields that are a list
        #     # when parsing an XML with multiple terms.
        #     #
        #     # Here I'm assuming that data_scadenza_pagamento and importo_pagamento_rata
        #     # need to be present, otherwise I'll get a key error,
        #     # while iban_cassa and nome_cassa can be not present in the invoice.
        #     terms_due_date =  xml_data.pop('data_scadenza_pagamento')
        #     terms_amount =  xml_data.pop('importo_pagamento_rata')
        #
        #     # All fields in the extracted records will always be present,
        #     # at least with a None value, since I force this in invoice_invoice_xml_processor.py .
        #     # The default None is just to be sure in case of massive changes to the codebase.
        #     terms_iban =  xml_data.pop('iban_cassa', None)
        #     if not terms_iban:
        #         terms_iban = [None]*len(terms_due_date)
        #     terms_cassa =  xml_data.pop('nome_cassa', None)
        #     if not terms_cassa:
        #         terms_cassa = [None]*len(terms_due_date)
        #
        #     # By popping data_scadenza_pagamento first,
        #     # I'm ensuring that data_scadenza_pagamento will be NULL
        #     # in the database when there are terms.
        #     fields_to_insert = extract_fields_name(prefix='fe_')
        #     for (sql_field, value) in xml_data.items():
        #         if sql_field in fields_to_insert:
        #             record_to_insert['fe_' + sql_field] = value
        #
        #     fields_to_insert = extract_fields_name(prefix='rfe_')
        #     for i in range(len(terms_due_date)):
        #         term_record = {}
        #         for (sql_field, value) in xml_data.items():
        #             if sql_field in fields_to_insert:
        #                 term_record['rfe_' + sql_field] = value
        #         term_record['rfe_' + 'data_scadenza_pagamento'] = terms_due_date[i]
        #         term_record['rfe_' + 'importo_pagamento_rata'] = terms_amount[i]
        #         term_record['rfe_' + 'iban_cassa'] = terms_iban[i]
        #         term_record['rfe_' + 'nome_cassa'] = terms_cassa[i]
        #         terms_to_insert.append(term_record)
        #
        #     results.append(result)
        #
        # elif invoice_type == 'ricevuta' and term_type == 'multiple_payments':
        #
        #     terms_due_date =  xml_data.pop('data_scadenza_pagamento')
        #     terms_amount =  xml_data.pop('importo_pagamento_rata')
        #     terms_iban =  xml_data.pop('iban_cassa', None)
        #     if not terms_iban:
        #         terms_iban = [None]*len(terms_due_date)
        #     terms_cassa =  xml_data.pop('nome_cassa', None)
        #     if not terms_cassa:
        #         terms_cassa = [None]*len(terms_due_date)
        #
        #     fields_to_insert = extract_fields_name(prefix='fr_')
        #     for (sql_field, value) in xml_data.items():
        #         if sql_field in fields_to_insert:
        #             record_to_insert['fr_' + sql_field] = value
        #
        #     fields_to_insert = extract_fields_name(prefix='rfr_')
        #     for i in range(len(terms_due_date)):
        #         term_record = {}
        #         for (sql_field, value) in xml_data.items():
        #             if sql_field in fields_to_insert:
        #                 term_record['rfr_' + sql_field] = value
        #         term_record['rfr_' + 'data_scadenza_pagamento'] = terms_due_date[i]
        #         term_record['rfr_' + 'importo_pagamento_rata'] = terms_amount[i]
        #         term_record['rfr_' + 'iban_cassa'] = terms_iban[i]
        #         term_record['rfr_' + 'nome_cassa'] = terms_cassa[i]
        #         terms_to_insert.append(term_record)
        #
        #     results.append(result)

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
