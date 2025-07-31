"""
Takes data structure as in output of invoice_xml_processor.py,
converts it to appropriate formats,
(todo) uploads only successful conversions,
and create a summary output of the full operation.
todo: also, uniqueness checks I think belongs here.

input: a call to process_xml_list(xml_files), found in invoice_xml_processor.py,
       that will produce the appropriate data structure.
output: message displaying a summary of the insert operation.

Usage:
python3 components/xml_processing/_invoice_uploader_op.py
due to the nature of the program, the local test will involve the database,
and data will be uploaded.
I need to specify in the code below the user_id of the testing account,
that is resetted every time I seed the database with reset_db.py

CONVERSION: since the insert part is trivial, I put here the conversion code?

IMPORTAN todo: I have to manage the workflow such that, I continue the processing for
all invoices correctly handled, and stop the processing only for the invoices
that are not correctly handled or that generate an error.
The original idea to add a field success in the dictionary was not bad.
This is true for this part of the tool but also for the processing one.
"""

from invoice_xml_processor import process_xml_list, print_processed_xml
from supabase import create_client
from datetime import datetime
from decimal import Decimal, getcontext
import toml
import os
import glob


# todo: rounding in division? I don't need rounding I want reminders.
# todo: use signals to handle operations safer like divisions or rounding?
def to_decimal(value) -> Decimal:
    # Is this global or do I need to do it every time?
    getcontext().prec = 2

    # todo: does it make sense to use 0.00 in this case or is it better to raise an error?
    if value is None or value == '':
        return Decimal('0.00')
    try:
        clean_value = str(value).strip().replace(',', '.')
        return Decimal(clean_value)
    except Exception as e:
        raise Exception('Invalid Decimal conversion') from e

# I could simplify this for sure, and in general I have
# to use the italian convention.
def to_italian_date(date_string):

    # todo: is this teh right format for the database?
    if not date_string or date_string.strip() == '':
        return None

    # todo: this -> datetime.strptime(date_string.strip(), '%Y-%m-%d')
    # should produce a ValueError in case the date is in the wrong format,
    # and since the exception is not handled, the program will terminate.
    return datetime.strptime(date_string.strip(), '%Y-%m-%d')

def save_to_database(results, client):
    # results can be a list with one or more dict or just one dict
    # and all data will be inserted.
    # The dict must have the key as the sql column name and the value
    # as the value I want to insert.

    successful_results = [r.get('data') for r in results if r['status'] == 'success']

    # if not successful_results:
    #     return {'saved': 0, 'errors': ['No successful results to save']}
    #
    # saved_count = 0
    # errors = []
    #
    # print("Starting inserting into table: ")
    # for result in successful_results:
    #     db_record = result['db_record']
    #
    #     # Insert into database directly
    #     if insert_data(supabase_client, db_record, 'fatture_emesse'):
    #         saved_count += 1
    #         print(f"Inserted following record: {db_record}")
    #     else:
    #         errors.append(f"{result['filename']}: Database insert failed")
    #
    # return {'saved': saved_count, 'errors': errors}

    try:
        result = client.table('fatture_emesse').insert(successful_results).execute()
        print("Insert successful:", result.data)
    except Exception as e:
        print("Error inserting data:", e)


if __name__ == "__main__":

    def get_supabase_client():
        secrets_path = Path(f"{PROJECT_ROOT}/.streamlit/secrets.toml")
        if not secrets_path.exists():
            raise FileNotFoundError("Missing .streamlit/secrets.toml file")

        secrets = toml.load(secrets_path)

        url = secrets.get("SUPABASE_URL")
        key = secrets.get("SUPABASE_ANON_KEY")
        if not url or not key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY in secrets.toml")

        return create_client(url, key)

    print("="*60)
    print("Uploader manual execution.")

    test_folder = f"{PROJECT_ROOT}/fatture_emesse"
    if not os.path.exists(test_folder):
        raise Exception(f"Folder not found: {test_folder}")

    xml_files = glob.glob(os.path.join(test_folder, "*.xml"))
    if not xml_files:
        raise Exception(f"No XML files found in: {test_folder}")
    print(f"Found {len(xml_files)} XML files in {test_folder}")

    xmls = process_xml_list(xml_files)
    print('XML processing results: ')
    print_processed_xml(xmls)

    supabase_client = get_supabase_client()
    save_to_database(xmls, supabase_client)





