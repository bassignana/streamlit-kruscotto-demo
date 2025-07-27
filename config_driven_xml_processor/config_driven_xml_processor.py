"""
sql -> mapping sql:xml -> format sql, extraction, conversion.

NOTE: the workflow is to take this data and upload it to a database,
so all types must be thought as compatible for an 'insert into',
not for the frontend.

For now, don't manage repeated nested structure. But in the future,
the following should be valid also.
If in 'mapping sql:xml' I specify just the last tag name in the hierarchy,
and not the full xml path,
then I have to check that I'm getting a tag that it is a 'leaf' tag in
the hierarchy tree.
I prefer to not use fully specified xml paths so that it is easier to
manage nested tags with multiple repeated elements.

INPUT: list of files or folder.
Streamlit file uploader returns a list of files,
even if there is just one file uploaded if the option
accept_multiple_files = True.
In order to be able to use this tool as a standalone tool/testing harness,
and also as a module to export the code for the app xml processing,
I'm going to expect to read files from a list.
The edgecase where I want to test just one file outside of a streamlit
application, has to be solved by putting a single file in one folder for now.

NO CONVERSIONS IN THIS FILE:
Conversion can be tricky, for example in the tag Numero
can be present values like 2/PA, so
1. doing two things, parsing and converting, is against unix philosophy
2. conversion is hard and used only where string is not a viable option.
"""



import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal, getcontext
import os
import glob
from xml_field_mapping import XML_FIELD_MAPPING

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

def find_element_text(root_element, tag_name) -> str:
    # In this function I expect that the tag that I want to extract
    # the text from, is unique in the whole xml file.
    #
    # Also, given the examples that I've been provided,
    # I expect one single, and useless, namespace at the root element level.
    #
    # I'll check for these conditions at the end of the function
    tag = []
    ns = []

    # todo: how to verify that a root like
    # <Element '{http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2}FatturaElettronica' at 0x1044ec9a0>
    # is well formed?
    # It has to be logged but not break the user flow.
    # old:
    # if root_element is None:
    #     return ''

    for element in root_element.iter():

        if '}' in element.tag:
            assert element.tag.count('}') == 1, AssertionError('Unexpected namespace and tag syntax')
            ns_name, tag_content = element.tag.split('}')
            # len(element) = 0 if has text but no children
            if len(element) == 0:
                tag.append(tag_content.strip())
                ns.append(ns_name)

        # From the docs, the preferred way of knowing if an element has zero children
        # is to do len(element) == 0. It's True if it is a 'leaf' element.
        # Here I'm checking that it is a leaf element because I've not implemented yet
        # parsing repeating structures.
        if element.tag == tag_name and len(element) == 0:
            tag.append(element.text.strip())

    if len(tag) == 0:
        raise Exception('No tag found')
    elif len(tag) > 1:
        raise Exception('Tag expected to be unique in the xml file')
    else:
        return tag[0]

def process_xml_file(xml_tree) -> dict:
    """Process a single XML file and extract configured fields."""

    extracted_data = {}

    for sql_field_name, sql_field_config in XML_FIELD_MAPPING.items():
        tag_name = sql_field_config['xml_tag']
        tag_value = find_element_text(xml_tree.getroot(), tag_name)
        extracted_data[sql_field_name] = tag_value

    # todo: how to hande the fact that inside find_element_text I raised an exception?
    # Do I need to propagate errors here? The program will halt and terminate?

        # sql_insert_data_type = field_config.get('data_type', 'string')

        # if sql_insert_data_type == 'string':
        #     extracted_data[sql_field_name] = tag_value
        # elif sql_insert_data_type == 'decimal':
        #     extracted_data[sql_field_name] = to_decimal(tag_value)
        # elif sql_insert_data_type == 'date':
        #     extracted_data[sql_field_name] = to_italian_date(tag_value)
        # else:
        #     raise Exception('Unhandled conversion case')

    return extracted_data

def process_xml_folder(folder_path) -> list:

    if not os.path.exists(folder_path):
        print(f"Folder not found: {folder_path}")
        return []
    
    # Find all XML files todo: names?
    xml_files = glob.glob(os.path.join(folder_path, "*.xml"))
    
    if not xml_files:
        print(f"No XML files found in: {folder_path}")
        return []
    
    print(f"Found {len(xml_files)} XML files in {folder_path}")
    print("-" * 50)
    
    xmls = []
    
    for filepath in xml_files:
        filename = os.path.basename(filepath)
        print(f"Processing: {filename}")

        xml_tree = ET.parse(filepath)
        data = process_xml_file(xml_tree)

        if len(data):
            xmls.append({
                'file': filename,
                'data': data
            })
        else:
            raise Exception('Error creating result dictionary for xml file')

    return xmls


def print_processed_xml(xml_array):
    for xml in xml_array:
        print(f"Filename: {xml.get('file')}")
        for sql_name, xml_tag_value in xml.get('data').items():
            print(f"{sql_name}: {xml_tag_value}")


# Main execution for testing
if __name__ == "__main__":
    
    print("XML Processor manual execution.")
    print("Specify in the code the folder or file to test.")
    print("="*60)
    
    test_folder = "../fatture_emesse"

    # Process all files in folder
    xmls = process_xml_folder(test_folder)
    
    # Print summary
    print_processed_xml(xmls)