import pytest
import glob
import os
from supabase import create_client
from invoice_record_creation import extract_xml_records
from invoice_xml_processor import process_xml_list
import streamlit as st

def test_document_date_assignment_when_empty_duedate():
    partita_iva_azienda = '12345678900'
    # TODO; when connected to the internet.
    #  Also, do I need to test this with the DB?.
    # supabase_client =  create_client(st.secrets['test_url'],
    #                                  st.secrets['test_service_key'])
    # supabase_client.table('fatture_emesse').delete().eq('user_id', st.secrets['test_id'])
    # supabase_client.table('fatture_ricevute').delete().eq('user_id', st.secrets['test_id'])

    # TODO; check again correctness of test data.
    xml_files = glob.glob(os.path.join('pytest_fixtures/test_document_date_assignment_when_empty_duedate', "*.xml"))
    for file in xml_files:
        is_data_scadenza_missing_in_original_invoice = True if '_without_' in file else False
        is_scadenze_multiple = 'scadenze_multiple' in file
        prefix = 'fe_' if 'emessa' in file else 'fr_'

        parsing_results, error = process_xml_list([file])
        result = extract_xml_records(parsing_results, partita_iva_azienda)

        # Note: this should work for both invoices with and without multiple terms.
        if is_data_scadenza_missing_in_original_invoice: # and is_scadenze_multiple:
            record = result[0]['record']
            terms = result[0]['terms']
            data_documento = record[prefix + 'data_documento']

            # Here I'm checking that, AT LEAST, one data_scadenza in terms is equal to data_documento,
            # because it might happen that sometimes some invoice's rows are correctly valued and
            # not all rows are empty.
            is_data_present = [term['r' + prefix + 'data_scadenza_pagamento'] == data_documento for term in terms]
            assert any(is_data_present)

        # NOTE; is this a good way to test this? I'm not testing invoices that were correctly
        # valued from the beginning...
