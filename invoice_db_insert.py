
from invoice_xml_processor import process_xml_list
from invoice_record_creation import extract_xml_records
from pathlib import Path
from supabase import create_client
from pprint import pprint
import toml
import glob
import os

if __name__ == '__main__':

    secrets_path = Path(".streamlit/secrets.toml")

    if not secrets_path.exists():
        raise FileNotFoundError("Missing .streamlit/secrets.toml file")

    secrets = toml.load(secrets_path)
    url = secrets.get("SUPABASE_URL")
    service_key = secrets.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not service_key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in secrets.toml")

    supabase_client =  create_client(url, service_key)

    # Invoices changed manually with this P IVA value
    partita_iva_azienda = '04228480408'
    # Taken from test db
    USER_ID = 'c7b70c85-68be-4047-ba1e-9ad0d66a3d13'
    xml_files = glob.glob(os.path.join('fe_scadenze_multiple/', "*.xml"))
    parsing_results, error = process_xml_list(xml_files)

    outs = []
    if parsing_results:
        xml_records = extract_xml_records(parsing_results, partita_iva_azienda)

        # successful_xml_parsings = [r for r in results if r['status'] == 'success']
        # error_xml_parsings = [r for r in results if r['status'] == 'error']
        #
        # successful_inserts_count = 0
        # error_inserts_data = []

        # Here the core logic is:
        # The data structure of xml below will contain fields for both
        # the single record to insert and the optional terms.
        # I can just check whether the terms field is empty.
        #
        # The field 'data_scadenza_pagamento' will be NULL
        # in case of terms.
        for xml in xml_records:

            out = {
                'filename': xml['filename'],
                'data': xml['data'],
                'status': xml['status'],
                'error_message': xml['error_message'],
                'record': xml['record'],
                'terms': xml['terms'],
                'invoice_type': xml['invoice_type'],
                'inserted_record': {},
                'inserted_terms': [],
            }

            try:
                if out['status'] == 'error':
                    outs.append(out)
                    continue # to the next invoice record(s)

                if out['invoice_type'] == 'emessa':
                    record_to_insert = out['record'].copy() # todo: copy necessary?

                    # User id is also inserted inside the following postgres function.
                    # I leave this here in case we might change approach so that
                    # we don't forget to add the user id.
                    # NOTE; this is a dirty way of doing it, because this is NOT the
                    # record that will be inserted. That record is created in the
                    # RPC function.
                    record_to_insert['user_id'] = USER_ID

                    result = supabase_client.rpc('insert_record_fixed', {
                        'table_name': 'fatture_emesse',
                        'record_data': out['record'],
                        'terms_table_name': 'rate_fatture_emesse',
                        'terms_data': out['terms'],
                        'test_user_id': USER_ID
                    }).execute()

                    if result.data and result.data.get('success'):
                        #todo: rerun on success?
                        # st.rerun()

                        out['inserted_record'] = record_to_insert
                        outs.append(out)
                        print('SUCCESS')
                        pprint(result.data)

                    else:
                        # xml['insert_table'] = 'fatture_emesse'
                        # xml['insert_result'] = result
                        # error_inserts_data.append(xml)

                        out['status'] = 'error'
                        out['error_message'] = f'Error during invoice INSERT for xml_record {result.data}'
                        print('ERROR')
                        pprint(result.data)
                        outs.append(out)
                        continue # to the next file

                    # All this branch is not needed anymore since I use the logic in the RPC function instead.
                    #
                    # if out['terms']:
                    #     terms_to_insert = out['terms'].copy()
                    #     for term in terms_to_insert:
                    #         term['user_id'] = USER_ID
                    #
                    #     # bulk insert
                    #     result = supabase_client.table('rate_fatture_emesse').insert(terms_to_insert).execute()
                    #     #
                    #     #
                    #     # TODO; IMPORTANT: USE TRANSACTION WHEN INSERTTING TERMS OR I"LL CREATE ORPHANS RECORDS
                    #     #
                    #     #
                    #     if len(result.data) == len(terms_to_insert):
                    #         # successful_inserts_count += 1
                    #         #todo: rerun on success?
                    #         # st.rerun()
                    #
                    #         out['inserted_terms'] = terms_to_insert
                    #         outs.append(out)
                    #     else:
                    #         # xml['insert_table'] = 'fatture_emesse'
                    #         # xml['insert_result'] = result
                    #         # error_inserts_data.append(xml)
                    #
                    #         out['status'] = 'error'
                    #         out['error_message'] = f'Error during terms INSERT for xml_record {out}'
                    #         outs.append(out)
                    #         continue # to the next file

                elif out['invoice_type'] == 'ricevuta':
                    record_to_insert = out['record'].copy() # todo: copy necessary?
                    record_to_insert['user_id'] = USER_ID

                    result = supabase_client.rpc('insert_record_fixed', {
                        'table_name': 'fatture_ricevute',
                        'record_data': out['record'],
                        'terms_table_name': 'rate_fatture_ricevute',
                        'terms_data': out['terms'],
                        'test_user_id': USER_ID
                    }).execute()

                    if result.data and result.data.get('success'):
                        out['inserted_record'] = record_to_insert
                        outs.append(out)
                    else:
                        out['status'] = 'error'
                        out['error_message'] = f'Error during invoice INSERT for xml_record {out}'
                        outs.append(out)
                        continue # to the next file

                else:
                    raise Exception(f"This branch should not be able to run, since there should be an early return for invoice not emessa and not ricevuta.")

            except Exception as e:
                # todo: should this kind of error shown to the user, probably not
                # print(f"Errore durante l'upload di {pprint(out)} nel database: {str(e)}")
                # error_inserts_data.append(xml)
                print(f'EXCEPTION: {e}')
                outs.append(out)
                continue # to the next xml

        # Probably I should tell the user only about errors that he/she can understand,
        # # like missing fields in XML files. Other than that only in logs or prints.
        # if successful_inserts_count > 0:
        #     st.success(f"{successful_inserts_count}/{len(uploaded_files)} fatture caricate con successo")
        #
        # if len(error_xml_parsings) > 0:
        #     st.warning(f"Leggendo l'XML delle seguenti {len(error_xml_parsings)} fatture si sono riscontrati errori")
        #     with st.expander('Dettagli errori lettura XML', expanded = False):
        #         for xml in error_xml_parsings:
        #             st.write(f"File: {xml['filename']}, errore: {xml['error_message']}")
        #
        # if len(error_inserts_data) > 0:
        #     st.warning(f"Caricando sul database le seguenti {len(error_xml_parsings)} fatture si sono riscontrati errori")
        #     with st.expander('Dettagli errori caricamento XML', expanded = False):
        #         for xml in error_inserts_data:
        #             st.write(f"File: {xml['filename']}, tabella: {xml['insert_table']}, risultato: {xml['insert_result']}")

    else:
        pass
        # print(f"Errore durante l'elaborazione delle fatture caricate")

    # pprint(outs)
