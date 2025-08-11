"""
Parses xml files to appropriate data structure below,
all in strings. <- todo check this
The conversion is not handled here. UNIX. Testable. All strings.

input: [file1.xml, ..., ] at least one file.
todo: checking that the list is not empty could be a good example of
      global error to handle with golang style errors.
output:

    xmls = []
    xmls.append({
                    'filename': filename,
                    'data': extracted_data,
                    'status' : 'success'
                    'error_message': ''
                })

If run in streamlit app, reads from uploader,
if run manually via terminal, will read via hardcoded folder.

REPEATED STRUCTURES:
Should manage both unique and not unique tags. For not unique tags, values are
appended in a list.

STREAMLIT UPLOADER COMPONENT:
Streamlit file uploader returns a list of files,
even if there is just one file uploaded if the option
accept_multiple_files = True.

STANDALONE TESTING:
Usage: python3 invoice_xml_processor.py
The edge case where I want to test just one file outside of a streamlit
application, has to be solved by putting a single file in one folder for now.
"""

import xml.etree.ElementTree as ET
import os
import glob
from xml_mapping_emesse import XML_FIELD_MAPPING
from pprint import pprint

def process_xml_list(xml_files: list) -> (list, str):
    """
    Take a list of xml files paths or a Streamlit UploadedFile object.
    For each file extract data based on config,
    augmenting extracted data with information about success or failure
    of extraction operation and uploaded file name.
    """
    extracted_info = []
    default_error_message = 'Unknown error'
    for file in xml_files:
        # Pattern: I prefer having a clearer exit structure from the nested loop
        # in case of error, paying with a more inefficient access structure.
        # Below the default case that, if not modified, will be returned for this XML file.
        #
        # I can refer to this current_file_data directly because it will reference
        # directly the item appended in the list.
        current_file_data = {
            'filename': None,
            'data': {},
            'status': 'error',
            'error_message': default_error_message
        }
        extracted_info.append(current_file_data)

        try:
            # Check if it's a Streamlit UploadedFile object or a file path
            if hasattr(file, 'name') and hasattr(file, 'read'):
                filename = file.name
                current_file_data['filename'] = filename
                xml_content = file.read()
                file.seek(0)  # Reset file pointer
                xml_tree = ET.ElementTree(ET.fromstring(xml_content))
            else: # Os file path
                filename = os.path.basename(file)
                current_file_data['filename'] = filename
                xml_tree = ET.parse(file)
        except Exception as e:
            current_file_data['error_message'] = f"XML Parsing Error: {str(e)}"
            # Don't return, but continue to the next file.
            continue

        try:
            for sql_field_name, sql_field_config in XML_FIELD_MAPPING.items():
                full_path = sql_field_config['xml_path']
                is_tag_required = sql_field_config['required']
                root_element = xml_tree.getroot()

                # Given the examples that I've been provided,
                # I expect one single, and useless, namespace at the root element level.
                #
                # ? In case of no tag present, does findall returns and empty []?
                expected_tags = root_element.findall(full_path)
                if len(expected_tags) == 0:
                    if is_tag_required:
                        print(f"ERROR: Required tag {full_path}, is not present in invoice {filename}")
                        current_file_data['data'] = {}
                        current_file_data['error_message'] = f"ERROR: Required tag {full_path}, is not present in invoice {filename}"

                        # This break will result in the next file being processed,
                        # since we have changed the error_message checked below.
                        break
                    else:
                        # todo: uncomment line below after debug
                        # print(f"TAG NOT FOUND: Not required tag {full_path}, is not present in invoice {filename}")
                        # We add the tag not found nonetheless valued with null, otherwise we have problems doing
                        # other types of checks.
                        # We can put all fields this way in an extraction, even if different fields belong to
                        # different tables: In the record creation phase, only the fields present in the sql create
                        # table file will be extracted from the xml parsing result.
                        # TODO: IMPORTANT: if we value not found tags with None, will they be converted
                        # correctly to postgres NONE?
                        current_file_data['data'][sql_field_name] = None
                        continue # to the next field for this file

                # Here I deal with possible multiple tags with the same path in the invoice.
                # I just put the values in an array that will be manage in another program.
                elif len(expected_tags) == 1:
                    tag_value = expected_tags[0].text
                    current_file_data['data'][sql_field_name] = tag_value
                elif len(expected_tags) > 1:
                    current_file_data['data'][sql_field_name] = [tag.text for tag in expected_tags]
                else:
                    assert False, "This branch should be unreachable."

            # When we break or when we finish the loop we get here.
            # The case in which the operation was successful for all fields is the one
            # where the error_message is still default_error_message
            if current_file_data['error_message'] == default_error_message:
                current_file_data['error_message'] = ''
                current_file_data['status'] = 'success'

        except Exception as e:
            current_file_data['error_message'] = f"Tag Searching Error: {str(e)}"
            continue # to the next file.

    # Here golang style errors makes little sense because I'm choosing to always returning a list of
    # results. I could implement golang style for global errors, for example if the XMLFIELDCONFIG is
    # corrupted or I cannot access the file system. These errors would impact the whole processing batch.
    # Just for reminder:
    # Usage:
    # def use_go_style():
    #     xml = "<root><child>value</child></root>"
    #     data, error = parse_xml_go_style(xml)
    #
    #     if error:
    #         print(f"Error: {error}")
    #         return False
    #
    #     print(f"Success: {data}")
    #     return True
    return extracted_info, None

def print_processed_xml(xml_array):
    for xml in xml_array:
        print(f"\n\n Filename: {xml.get('filename')}")
        pprint(xml)

if __name__ == "__main__":
    print("\n"*3)
    print("XML Processor manual execution.")

    test_folder = f"fe_scadenze_multiple/"
    if not os.path.exists(test_folder):
        raise Exception(f"Folder not found: {test_folder}")

    xml_files = glob.glob(os.path.join(test_folder, "*.xml"))
    if not xml_files:
        raise Exception(f"No XML files found in: {test_folder}")

    print(f"Found {len(xml_files)} XML files in {test_folder}")
    print("\n")

    # todo: in streamlit, add warning that if I don't find the list of file,
    # especially with one single file, I have to set the upload_multiple_files
    # to True in the uploader component.
    xmls, error = process_xml_list(xml_files)
    if not error:
        print_processed_xml(xmls)
        print(f"Found {len(xml_files)} XML files in {test_folder}")
        print(f"Created unsuccessful or successful entries for {len(xmls)} XML files")
        print('\n\n\n\n')
        for xml_full in xmls:
            xml = xml_full['data']

            assert len(xml) == len(XML_FIELD_MAPPING.items()), "All fields in config must be present, at least with None, in the extracted data."
            assert xml['partita_iva_committente'] != xml['partita_iva_prestatore'], "P IVA Prestatore e Committente non possono coincidere."

            print(xml_full['filename'])
            if xml.get('partita_iva_committente', None):
                print(f'P IVA Committente {xml['partita_iva_committente']}')
            print(f'P IVA Prestatore {xml['partita_iva_prestatore']}')
            if isinstance(xml['data_scadenza_pagamento'], list):
                print('terms: YES')
            else:
                print('terms: NO')
        print('\n')


    else:
        print(error)


