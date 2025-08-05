import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from supabase import create_client, Client
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
XML_FIELD_MAPPING = {
    'invoice_number': {
        'xml_tag': 'Numero',
        'data_type': 'string',
        'required': True,
        'section': 'body'
    },
    'document_date': {
        'xml_tag': 'Data',
        'data_type': 'date',
        'required': True,
        'section': 'body'
    },
    'total_amount': {
        'xml_tag': 'ImportoTotaleDocumento',
        'data_type': 'decimal',
        'required': True,
        'section': 'body'
    },
    'due_date': {
        'xml_tag': 'DataScadenzaPagamento',
        'data_type': 'date',
        'required': False,
        'section': 'body'
    }
}

@st.cache_resource
def init_supabase():
    """Initialize Supabase client"""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_ANON_KEY"]
        return create_client(url, key)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase: {str(e)}")
        raise

# XML processor
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
    
    return date_string

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

def extract_field_value(sections, field_name, field_config):
    """Extract a single field value based on configuration."""
    
    section_name = field_config.get('section', 'body')
    section_element = sections.get(section_name)
    
    if section_element is None:
        return None
    
    tag_name = field_config['xml_tag']
    raw_value = find_element_text(section_element, tag_name)
    
    if not raw_value:
        return None
    
    data_type = field_config.get('data_type', 'string')
    
    if data_type == 'string':
        return raw_value
    elif data_type == 'decimal':
        return safe_decimal(raw_value)
    elif data_type == 'date':
        return parse_date_to_iso(raw_value)
    else:
        return raw_value

def process_xml_file(xml_content, filename, user_id):
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
        
        # Check required fields
        missing_required = []
        for field_name, field_config in XML_FIELD_MAPPING.items():
            if field_config.get('required', False):
                if field_name not in extracted_data or not extracted_data[field_name]:
                    missing_required.append(field_name)
        
        if missing_required:
            return {
                'filename': filename,
                'status': 'error',
                'error': f'Missing required fields: {", ".join(missing_required)}'
            }
        
        # Prepare database record
        db_record = {
            'user_id': user_id,
            'invoice_number': extracted_data.get('invoice_number', ''),
            'document_date': extracted_data.get('document_date'),
            'total_amount': extracted_data.get('total_amount', 0.0),
            'due_date': extracted_data.get('due_date')
        }
        
        return {
            'filename': filename,
            'status': 'success',
            'extracted_data': extracted_data,
            'db_record': db_record
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

def process_uploaded_files(uploaded_files, user_id):
    """Process all uploaded files."""
    
    results = []
    
    for uploaded_file in uploaded_files:
        try:
            # Read file content
            uploaded_file.seek(0)
            raw_content = uploaded_file.read()
            
            # Handle different encodings
            xml_content = None
            for encoding in ['utf-8', 'utf-8-sig', 'cp1252', 'iso-8859-1']:
                try:
                    xml_content = raw_content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if xml_content is None:
                results.append({
                    'filename': uploaded_file.name,
                    'status': 'error',
                    'error': 'Unable to decode file'
                })
                continue
            
            # Clean XML content
            xml_content = xml_content.strip()
            if xml_content.startswith('\ufeff'):
                xml_content = xml_content[1:]
            
            # Process the file
            result = process_xml_file(xml_content, uploaded_file.name, user_id)
            results.append(result)
            
        except Exception as e:
            results.append({
                'filename': uploaded_file.name,
                'status': 'error',
                'error': f'File reading error: {str(e)}'
            })
    
    return results

def insert_fattura_emessa(supabase_client, fattura_data):
    """Insert a single fattura into database."""
    logger.info(f"Inserting fattura: {fattura_data['invoice_number']}")
    
    try:
        # Create a copy to avoid modifying original
        data_to_insert = fattura_data.copy()
        
        # Add timestamps
        data_to_insert['created_at'] = datetime.now().isoformat()
        data_to_insert['updated_at'] = datetime.now().isoformat()
        
        result = supabase_client.table('fatture_emesse').insert(data_to_insert).execute()
        
        logger.info(f"Database result: {result}")
        
        if result.data:
            logger.info(f"✅ Successfully inserted: {fattura_data['invoice_number']}")
            return True
        else:
            logger.error(f"❌ No data returned for: {fattura_data['invoice_number']}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database error for {fattura_data['invoice_number']}: {str(e)}")
        
        # Print more detailed error info
        import traceback
        full_error = traceback.format_exc()
        logger.error(f"Full traceback: {full_error}")
        
        return False

def save_to_database(results, supabase_client):
    """Save successful results to database automatically."""
    
    logger.info("=== STARTING DATABASE SAVE ===")
    
    successful_results = [r for r in results if r['status'] == 'success']
    
    if not successful_results:
        return {'saved': 0, 'errors': ['No successful results to save']}
    
    saved_count = 0
    errors = []
    
    for result in successful_results:
        db_record = result['db_record']
        
        # Insert into database directly
        if insert_fattura_emessa(supabase_client, db_record):
            saved_count += 1
        else:
            errors.append(f"{result['filename']}: Database insert failed")
    
    logger.info(f"=== SAVE COMPLETE: {saved_count} saved, {len(errors)} errors ===")
    
    return {'saved': saved_count, 'errors': errors}

def main():
    """Main Streamlit application."""
    
    st.set_page_config(
        page_title="Upload Fatture Emesse",
        page_icon="📄",
        layout="wide"
    )
    
    logger.info("=== APPLICATION STARTED ===")
    
    # Check authentication
    if 'user' not in st.session_state or not st.session_state.user:
        logger.warning("User not authenticated")
        st.error("🔐 Please login first")
        st.stop()
    
    user_id = st.session_state.user.id
    logger.info(f"User authenticated: {user_id}")
    logger.info(f"User details: {st.session_state.user}")
    
    # Initialize Supabase
    try:
        supabase_client = init_supabase()
        logger.info("Supabase client ready")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase: {str(e)}")
        st.error(f"Database connection failed: {str(e)}")
        st.stop()
    
    st.title("📄 Upload Fatture Emesse XML")
    
    # Add debug info
    with st.expander("🔍 Debug Info", expanded=False):
        st.write(f"**User ID:** {user_id}")
        st.write(f"**User Info:** {st.session_state.user}")
        st.write(f"**Supabase URL:** {st.secrets.get('SUPABASE_URL', 'Not found')}")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Select XML files",
        type=['xml'],
        accept_multiple_files=True,
        help="Upload one or more XML invoice files"
    )
    
    if uploaded_files:
        logger.info(f"Files uploaded: {[f.name for f in uploaded_files]}")
        st.success(f"📄 {len(uploaded_files)} file(s) uploaded")
        
        # Process button
        if st.button("🚀 Process Files and Save to Database", type="primary", use_container_width=True):
            
            # Process files
            with st.spinner("Processing files and saving to database..."):
                results = process_uploaded_files(uploaded_files, user_id)
                
                # Automatically save to database
                save_result = save_to_database(results, supabase_client)
            
            # Show results
            successful = [r for r in results if r['status'] == 'success']
            errors = [r for r in results if r['status'] == 'error']
            
            # Display summary
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("✅ Processed", len(successful))
            with col2:
                st.metric("💾 Saved to DB", save_result['saved'])
            with col3:
                st.metric("❌ Errors", len(errors))
            with col4:
                if successful:
                    total = sum(r['db_record']['total_amount'] for r in successful)
                    st.metric("💰 Total", f"€ {total:,.2f}")
            
            # Success message
            if save_result['saved'] > 0:
                st.success(f"🎉 Successfully processed and saved {save_result['saved']} invoices to database!")
                
            
            # Show successful results
            if successful:
                st.subheader("✅ Processed Invoices")
                
                display_data = []
                for result in successful:
                    db_record = result['db_record']
                    display_data.append({
                        'File': result['filename'],
                        'Invoice Number': db_record['invoice_number'],
                        'Date': db_record['document_date'],
                        'Amount': f"€ {db_record['total_amount']:,.2f}",
                        'Due Date': db_record['due_date'] or '-'
                    })
                
                st.dataframe(pd.DataFrame(display_data), use_container_width=True, hide_index=True)
            
            # Show errors
            if errors:
                st.subheader("❌ Processing Errors")
                error_data = []
                for result in errors:
                    error_data.append({
                        'File': result['filename'],
                        'Error': result['error']
                    })
                st.dataframe(pd.DataFrame(error_data), use_container_width=True, hide_index=True)
            
            # Show database errors
            if save_result['errors']:
                st.subheader("❌ Database Errors")
                for error in save_result['errors']:
                    st.error(f"• {error}")

if __name__ == "__main__":
    main()