import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import os
import glob
from xml_field_mapping import XML_FIELD_MAPPING


def safe_decimal(value):
    """Safely convert value to Decimal with 2 decimal places."""
    if value is None or value == '':
        return 0.0
    try:
        clean_value = str(value).strip().replace(',', '.')
        return float(Decimal(clean_value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    except:
        return 0.0


def parse_date_to_iso(date_string):
    """Parse date string to ISO format (YYYY-MM-DD)."""
    if not date_string or date_string.strip() == '':
        return None
    
    date_string = date_string.strip()
    
    date_formats = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']
    
    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_string, fmt)
            return parsed_date.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    return date_string  # Return original if no format matches


def find_element_text(root_element, tag_name):
    """Find text content of an XML element by tag name."""
    if root_element is None:
        return ''
    
    # Direct search
    found = root_element.find(f'.//{tag_name}')
    if found is not None and found.text:
        return found.text.strip()
    
    # Iterative search ignoring namespaces
    for element in root_element.iter():
        clean_tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        if clean_tag == tag_name and element.text:
            return element.text.strip()
    
    return ''


def extract_xml_sections(root):
    """Extract main XML sections (header and body)."""
    sections = {'header': None, 'body': None}
    
    for element in root.iter():
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        if tag == 'FatturaElettronicaHeader' and sections['header'] is None:
            sections['header'] = element
        elif tag == 'FatturaElettronicaBody' and sections['body'] is None:
            sections['body'] = element
    
    return sections


def extract_field_value(sections, field_config):
    """Extract a single field value based on configuration."""
    
    # Get the section to search in
    section_name = field_config.get('section', 'body')
    section_element = sections.get(section_name)
    
    if section_element is None:
        return None
    
    # Extract raw value
    tag_name = field_config['xml_tag']
    raw_value = find_element_text(section_element, tag_name)
    
    if not raw_value:
        return None
    
    # Convert data type
    data_type = field_config.get('data_type', 'string')
    
    if data_type == 'string':
        return raw_value
    elif data_type == 'decimal':
        return safe_decimal(raw_value)
    elif data_type == 'date':
        return parse_date_to_iso(raw_value)
    else:
        return raw_value


def process_xml_file(xml_content, filename):
    """Process a single XML file and extract configured fields."""
    
    try:
        # Parse XML
        root = ET.fromstring(xml_content)
        
        # Extract sections
        sections = extract_xml_sections(root)
        
        if sections['header'] is None or sections['body'] is None:
            return {
                'filename': filename,
                'status': 'error',
                'error': 'Missing header or body section'
            }
        
        # Extract all configured fields
        extracted_data = {}
        
        for field_name, field_config in XML_FIELD_MAPPING.items():
            value = extract_field_value(sections, field_name, field_config)
            extracted_data[field_name] = value
        
        return {
            'filename': filename,
            'status': 'success',
            'data': extracted_data
        }
        
    except ET.ParseError as e:
        return {
            'filename': filename,
            'status': 'error',
            'error': f'XML parsing error: {str(e)}'
        }
    except Exception as e:
        return {
            'filename': filename,
            'status': 'error',
            'error': f'Processing error: {str(e)}'
        }


def read_xml_file(filepath):
    """Read XML file with proper encoding handling."""
    
    with open(filepath, 'rb') as f:
        raw_content = f.read()
    
    # Try different encodings
    for encoding in ['utf-8', 'utf-8-sig', 'cp1252', 'iso-8859-1']:
        try:
            xml_content = raw_content.decode(encoding)
            # Clean content
            xml_content = xml_content.strip()
            if xml_content.startswith('\ufeff'):  # Remove BOM
                xml_content = xml_content[1:]
            return xml_content
        except UnicodeDecodeError:
            continue
    
    raise Exception("Could not decode file with supported encodings")


def process_xml_folder(folder_path):
    """Process all XML files in a folder."""
    
    if not os.path.exists(folder_path):
        print(f"❌ Folder not found: {folder_path}")
        return []
    
    # Find all XML files
    xml_files = glob.glob(os.path.join(folder_path, "*.xml"))
    
    if not xml_files:
        print(f"❌ No XML files found in: {folder_path}")
        return []
    
    print(f"📁 Found {len(xml_files)} XML files in {folder_path}")
    print("-" * 50)
    
    results = []
    
    for filepath in xml_files:
        filename = os.path.basename(filepath)
        print(f"\n🔄 Processing: {filename}")
        
        try:
            # Read file
            xml_content = read_xml_file(filepath)
            
            # Process file
            result = process_xml_file(xml_content, filename)
            results.append(result)
            
            # Print result
            if result['status'] == 'success':
                print("✅ Success")
                data = result['data']
                for field, value in data.items():
                    print(f"   {field}: {value}")
            else:
                print(f"❌ Error: {result['error']}")
                
        except Exception as e:
            error_result = {
                'filename': filename,
                'status': 'error',
                'error': f'File reading error: {str(e)}'
            }
            results.append(error_result)
            print(f"❌ File error: {str(e)}")
    
    return results


def print_summary(results):
    """Print a summary of processing results."""
    
    if not results:
        print("\n📊 No results to summarize")
        return
    
    successful = [r for r in results if r['status'] == 'success']
    errors = [r for r in results if r['status'] == 'error']
    
    print("\n" + "="*60)
    print("📊 PROCESSING SUMMARY")
    print("="*60)
    print(f"Total files: {len(results)}")
    print(f"✅ Successful: {len(successful)}")
    print(f"❌ Errors: {len(errors)}")
    
    if successful:
        print(f"\n💰 Total amount from successful files:")
        total_amount = 0
        for result in successful:
            amount = result['data'].get('total_amount', 0)
            if amount:
                total_amount += amount
        print(f"   € {total_amount:,.2f}")
    
    if errors:
        print(f"\n❌ Error details:")
        for result in errors:
            print(f"   {result['filename']}: {result['error']}")


def test_single_file(filepath):
    """Test processing of a single XML file."""
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return
    
    filename = os.path.basename(filepath)
    print(f"🔄 Testing single file: {filename}")
    print("-" * 50)
    
    try:
        xml_content = read_xml_file(filepath)
        result = process_xml_file(xml_content, filename)
        
        if result['status'] == 'success':
            print("✅ Success")
            print("\nExtracted data:")
            for field, value in result['data'].items():
                print(f"   {field}: {value}")
        else:
            print(f"❌ Error: {result['error']}")
            
    except Exception as e:
        print(f"❌ File error: {str(e)}")


# Main execution for testing
if __name__ == "__main__":
    
    print("🧾 Simple XML Invoice Processor")
    print("="*60)
    
    # Test with a folder (change this path to your XML folder)
    test_folder = "./fatture_emesse"  # Change this to your folder path
    
    print(f"\n📂 Current configuration fields:")
    for field, config in XML_FIELD_MAPPING.items():
        required = "yes" if config.get('required', False) else "no"
        print(f"   {field} ({config['data_type']}) - Required: {required}")
    
    print(f"\n🔍 Looking for XML files in: {test_folder}")
    
    # Process all files in folder
    results = process_xml_folder(test_folder)
    
    # Print summary
    print_summary(results)
    
    # Uncomment to test a single file instead
    # test_single_file("./path/to/your/invoice.xml")