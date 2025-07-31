"""
# todo: update docs

Parses xml files to appropriate data structure below, all in strings.
The conversion is not handled here. UNIX. Testable. All strings.

input: [file1.xml, ..., ] at least one file.
output:
    extracted_data = {}
    extracted_data[sql_field_name] = tag_value

    xmls = []
    xmls.append({
                    'filename': filename,
                    'data': extracted_data,
                    'status' : 'success'
                })

extracted_data['status'] = 'success'

If run in streamlit app, reads from uploader,
if run manually via terminal, will read via hardcoded folder.

REPEATED STRUCTURES:
For now, don't manage repeated nested structure. But in the future,
the following should be valid also.

STREAMLIT UPLOADER COMPONENT:
Streamlit file uploader returns a list of files,
even if there is just one file uploaded if the option
accept_multiple_files = True.

STANDALONE TESTING:
Usage: python3 components/xml_processing/invoice_xml_processor.py
The edge case where I want to test just one file outside of a streamlit
application, has to be solved by putting a single file in one folder for now.

NO CONVERSIONS IN THIS FILE:
Conversion can be tricky, for example in the tag Numero
can be present values like 2/PA, so
1. doing two things, parsing and converting, is against unix philosophy
2. conversion is hard and used only where string is not a viable option.

DONE: add handling of failed processing without blocking successful uploads.
"""

import xml.etree.ElementTree as ET
import os
import glob
from xml_mapping_emesse import XML_FIELD_MAPPING

def process_xml_list(xml_files: list) -> list:
    """
    Take a list of xml files paths or a Streamlit UploadedFile object.
    For each file extract data based on config,
    augmenting extracted data with information about success or failure
    of extraction operation and uploaded file name.
    """
    extracted_info = []

    for file in xml_files:

        # Check if it's a Streamlit UploadedFile object
        if hasattr(file, 'name') and hasattr(file, 'read'):
            filename = file.name
            xml_content = file.read()
            file.seek(0)  # Reset file pointer
            xml_tree = ET.ElementTree(ET.fromstring(xml_content))
        else:
            # It's an os file path
            filename = os.path.basename(file)
            xml_tree = ET.parse(file)


        try:
            extracted_xml_data = {}
            for sql_field_name, sql_field_config in XML_FIELD_MAPPING.items():
                full_path = sql_field_config['xml_path']
                root_element = xml_tree.getroot()

                # Here I expect that the tag that I want to extract
                # the text from, is unique in the whole xml file.
                # Currently there is no automatic check for that, instead you have
                # to look at the documentation at
                # https://www.fatturapa.gov.it/it/norme-e-regole/documentazione-fattura-elettronica/
                # and be sure that the field that you are searching for will be present 0 or 1 times.
                #
                # Also, given the examples that I've been provided,
                # I expect one single, and useless, namespace at the root element level.
                try:
                    expected_tag = root_element.find(full_path)
                    if expected_tag is not None:
                        tag_value = expected_tag.text
                        extracted_xml_data[sql_field_name] = tag_value
                except:
                    print(f'Error on full path: {full_path}')

            extracted_info.append({
                'filename': filename,
                'data': extracted_xml_data,
                'status' : 'success'
            })

        except Exception as e:  # More specific exception handling
            extracted_info.append({
                'filename': filename,
                'data': {},
                'status': 'error',
                'error_message': str(e)
            })

    return extracted_info

def print_processed_xml(xml_array):
    for xml in xml_array:
        print(f"Filename: {xml.get('filename')}")
        for sql_name, xml_tag_value in xml.get('data').items():
            print(f"{sql_name}: {xml_tag_value}")

if __name__ == "__main__":
    
    print("XML Processor manual execution.")
    print("="*60)
    
    test_folder = f"fatture_emesse/"
    if not os.path.exists(test_folder):
        raise Exception(f"Folder not found: {test_folder}")

    xml_files = glob.glob(os.path.join(test_folder, "*.xml"))
    if not xml_files:
        raise Exception(f"No XML files found in: {test_folder}")

    print(f"Found {len(xml_files)} XML files in {test_folder}")
    print("-" * 50)

    # todo: in streamlit, add warning that if I don't find the list of file,
    # especially with one single file, I have to set the upload_multiple_files
    # to True in the uploader component.
    xmls = process_xml_list(xml_files)
    print_processed_xml(xmls)
    # print(xmls)