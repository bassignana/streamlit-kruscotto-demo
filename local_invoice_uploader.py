"""
Test file to run locally without streamlit.
Production logic in render_generic_xml_upload_section() in invoice_utils.py
"""

from invoice_xml_processor import process_xml_list
from invoice_record_creation import extract_xml_records
from pathlib import Path
from supabase import create_client
from pprint import pprint
import toml
import glob
import os

secrets_path = Path(".streamlit/secrets.toml")
secrets = toml.load(secrets_path)
url = secrets.get("SUPABASE_URL")
service_key = secrets.get("SUPABASE_SERVICE_ROLE_KEY")

if not secrets_path.exists():
    raise FileNotFoundError("Missing .streamlit/secrets.toml file")
if not url or not service_key:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in secrets.toml")

supabase_client =  create_client(url, service_key)

# Invoices changed manually with this P IVA value
partita_iva_azienda = '12345678900'

# Taken from test db
USER_ID = '86eda584-e990-4e13-9d93-d61b7811da8e'
xml_files = glob.glob(os.path.join('fatture_ricevute/', "*.xml"))

if __name__ == '__main__':

    parsing_results, error = process_xml_list(xml_files)

    outs = []
    if parsing_results:
        xml_records = extract_xml_records(parsing_results, partita_iva_azienda)

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
                    record_to_insert = out['record'].copy()

                    # User id is also inserted inside the following postgres function.
                    # I leave this here in case we might change approach so that
                    # we don't forget to add the user id.
                    # NOTE; this is a dirty way of doing it, because this is NOT the
                    # record that will be inserted. That record is created in the
                    # RPC function.
                    #
                    # Todo: related to the "issue" of adding user_id both here and
                    # in the procedure, it has to be clear what implicit rules are
                    # respected inside the RPC function, for example if triggers for
                    # created_at and updated_at will function correctly, and if the
                    # automatic id setting with get_random_uuid() will work etc.
                    # The best thing should be that all RPC functions will work the same.
                    record_to_insert['user_id'] = USER_ID

                    result = supabase_client.rpc('insert_record', {
                        'table_name': 'fatture_emesse',
                        'record_data': out['record'],
                        'terms_table_name': 'rate_fatture_emesse',
                        'terms_data': out['terms'],
                        'test_user_id': USER_ID
                    }).execute()

                    if result.data and result.data.get('success'):
                        out['inserted_record'] = record_to_insert
                        outs.append(out)
                        print('SUCCESS')
                        pprint(result.data)

                    else:
                        out['status'] = 'error'
                        out['error_message'] = f'Error during invoice INSERT for xml_record {result.data}'
                        print('ERROR')
                        pprint(result.data)
                        outs.append(out)
                        continue # to the next file

                elif out['invoice_type'] == 'ricevuta':
                    record_to_insert = out['record'].copy()
                    record_to_insert['user_id'] = USER_ID

                    result = supabase_client.rpc('insert_record', {
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

    else:
        pass
        # print(f"Errore durante l'elaborazione delle fatture caricate")

    # pprint(outs)
