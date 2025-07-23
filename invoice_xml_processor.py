import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional


def safe_decimal(value) -> Decimal:
    """Safely convert value to Decimal with 2 decimal places."""
    if value is None or value == '':
        return Decimal('0.00')
    try:
        return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except:
        return Decimal('0.00')


def parse_date(date_string: str) -> Optional[str]:
    """Parse date and return formatted string."""
    try:
        dt = datetime.strptime(date_string, '%Y-%m-%d')
        return dt.strftime('%d/%m/%Y')
    except:
        return date_string if date_string else None


def get_element_text(element, tag_name: str) -> str:
    """Get text from element by tag name, handling any namespace issues."""
    if element is None:
        return ''
    
    # Method 1: Direct search
    found = element.find(f'.//{tag_name}')
    if found is not None and found.text:
        return found.text.strip()
    
    # Method 2: Iterate through all elements and match tag name
    for elem in element.iter():
        # Get clean tag name (remove namespace if present)
        clean_tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if clean_tag == tag_name and elem.text:
            return elem.text.strip()
    
    return ''


def extract_invoice_data_simple(xml_content: str, file_name: str) -> Dict:
    """Extract invoice data using simple, robust approach."""
    
    try:
        # Parse XML
        root = ET.fromstring(xml_content)
        
        # Initialize result
        result = {
            'file_name': file_name,
            'status': 'success',
            'document_number': '',
            'document_date': '',
            'supplier_name': '',
            'customer_name': '',
            'total_amount': 0.00,
            'taxable_amount': 0.00,
            'vat_amount': 0.00,
            'payment_due_date': '',
            'payment_method': '',
            'iban': '',
            'currency': 'EUR',
            'withholding_amount': 0.00
        }
        
        # Find main sections by iterating (most reliable method)
        header = None
        body = None
        
        for element in root.iter():
            tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            if tag == 'FatturaElettronicaHeader' and header is None:
                header = element
            elif tag == 'FatturaElettronicaBody' and body is None:
                body = element
        
        if header is None or body is None:
            return {
                'file_name': file_name,
                'status': 'error',
                'error_message': f'Cannot find header ({header is not None}) or body ({body is not None})'
            }
        
        # Extract document info from body
        result['document_number'] = get_element_text(body, 'Numero')
        
        date_str = get_element_text(body, 'Data')
        if date_str:
            result['document_date'] = parse_date(date_str) or date_str
        
        result['currency'] = get_element_text(body, 'Divisa') or 'EUR'
        
        # Total amount
        total_str = get_element_text(body, 'ImportoTotaleDocumento')
        if total_str:
            result['total_amount'] = float(safe_decimal(total_str))
        
        # Withholding tax
        withholding_str = get_element_text(body, 'ImportoRitenuta')
        if withholding_str:
            result['withholding_amount'] = float(safe_decimal(withholding_str))
        
        # Find supplier section
        supplier_section = None
        for element in header.iter():
            tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            if tag == 'CedentePrestatore':
                supplier_section = element
                break
        
        if supplier_section is not None:
            # Try company name first
            supplier_name = get_element_text(supplier_section, 'Denominazione')
            if not supplier_name:
                # Try individual name
                first_name = get_element_text(supplier_section, 'Nome')
                last_name = get_element_text(supplier_section, 'Cognome')
                if first_name or last_name:
                    supplier_name = f"{first_name} {last_name}".strip()
            result['supplier_name'] = supplier_name
        
        # Find customer section
        customer_section = None
        for element in header.iter():
            tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            if tag == 'CessionarioCommittente':
                customer_section = element
                break
        
        if customer_section is not None:
            # Try company name first
            customer_name = get_element_text(customer_section, 'Denominazione')
            if not customer_name:
                # Try individual name
                first_name = get_element_text(customer_section, 'Nome')
                last_name = get_element_text(customer_section, 'Cognome')
                if first_name or last_name:
                    customer_name = f"{first_name} {last_name}".strip()
            result['customer_name'] = customer_name
        
        # Find VAT summary
        vat_section = None
        for element in body.iter():
            tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            if tag == 'DatiRiepilogo':
                vat_section = element
                break
        
        if vat_section is not None:
            taxable_str = get_element_text(vat_section, 'ImponibileImporto')
            vat_str = get_element_text(vat_section, 'Imposta')
            
            if taxable_str:
                result['taxable_amount'] = float(safe_decimal(taxable_str))
            if vat_str:
                result['vat_amount'] = float(safe_decimal(vat_str))
        
        # Find payment info
        payment_section = None
        for element in body.iter():
            tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            if tag == 'DettaglioPagamento':
                payment_section = element
                break
        
        if payment_section is not None:
            result['payment_method'] = get_element_text(payment_section, 'ModalitaPagamento')
            result['iban'] = get_element_text(payment_section, 'IBAN')
            
            due_date_str = get_element_text(payment_section, 'DataScadenzaPagamento')
            if due_date_str:
                result['payment_due_date'] = parse_date(due_date_str) or due_date_str
        
        return result
        
    except ET.ParseError as e:
        return {
            'file_name': file_name,
            'status': 'error',
            'error_message': f'XML parsing error: {str(e)}'
        }
    except Exception as e:
        return {
            'file_name': file_name,
            'status': 'error',
            'error_message': f'Unexpected error: {str(e)}'
        }


def invoice_xml_processor_page():
    """Main Streamlit page for processing XML invoices - SIMPLIFIED VERSION."""
    
    # Initialize session state
    if 'processed_invoices_simple' not in st.session_state:
        st.session_state.processed_invoices_simple = []
    
    st.title("🧾 Elaborazione Fatture XML - Versione Semplificata")
    st.markdown("Carica le fatture elettroniche XML per estrarre i dati essenziali per il flusso di cassa.")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "📁 Seleziona fatture XML",
        type=['xml'],
        accept_multiple_files=True,
        help="Fatture elettroniche italiane in formato XML"
    )
    
    if uploaded_files:
        st.success(f"📄 {len(uploaded_files)} file caricato/i")
        
        # Show file details
        with st.expander("📋 File caricati", expanded=True):
            for i, file in enumerate(uploaded_files, 1):
                st.write(f"**{i}.** {file.name} ({file.size/1024:.1f} KB)")
        
        # Process button
        if st.button("🔄 Elabora Fatture", type="primary", use_container_width=True):
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            processed_invoices = []
            
            for i, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Elaborazione {uploaded_file.name}...")
                progress_bar.progress((i) / len(uploaded_files))
                
                try:
                    # Reset file pointer and read content
                    uploaded_file.seek(0)
                    raw_content = uploaded_file.read()
                    
                    # Handle encoding
                    try:
                        xml_content = raw_content.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            xml_content = raw_content.decode('utf-8-sig')
                        except UnicodeDecodeError:
                            xml_content = raw_content.decode('cp1252')
                    
                    # Clean content
                    xml_content = xml_content.strip()
                    if xml_content.startswith('\ufeff'):
                        xml_content = xml_content[1:]
                    
                    # Extract data using simple method
                    invoice_data = extract_invoice_data_simple(xml_content, uploaded_file.name)
                    processed_invoices.append(invoice_data)
                    
                except Exception as e:
                    processed_invoices.append({
                        'file_name': uploaded_file.name,
                        'status': 'error',
                        'error_message': f'File reading error: {str(e)}'
                    })
            
            # Complete processing
            progress_bar.progress(1.0)
            status_text.text("✅ Elaborazione completata!")
            
            # Store results
            st.session_state.processed_invoices_simple = processed_invoices
            
            # Show summary
            successful = sum(1 for inv in processed_invoices if inv.get('status') == 'success')
            failed = len(processed_invoices) - successful
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("✅ Successo", successful)
            with col2:
                st.metric("❌ Errori", failed)
            with col3:
                if successful > 0:
                    total = sum(inv.get('total_amount', 0) for inv in processed_invoices if inv.get('status') == 'success')
                    st.metric("💰 Totale", f"€ {total:,.2f}")
                else:
                    st.metric("💰 Totale", "€ 0,00")
    
    # Display results if available
    if st.session_state.processed_invoices_simple:
        st.markdown("---")
        st.subheader("📊 Risultati Elaborazione")
        
        # Create DataFrame
        df_data = []
        for inv in st.session_state.processed_invoices_simple:
            if inv.get('status') == 'success':
                row = {
                    'File': inv['file_name'],
                    'Numero': inv['document_number'],
                    'Data': inv['document_date'],
                    'Fornitore': inv['supplier_name'],
                    'Cliente': inv['customer_name'],
                    'Totale €': inv['total_amount'],
                    'Imponibile €': inv['taxable_amount'],
                    'IVA €': inv['vat_amount'],
                    'Ritenuta €': inv.get('withholding_amount', 0.00),
                    'Scadenza': inv['payment_due_date'],
                    'Metodo Pag.': inv['payment_method'],
                    'IBAN': inv['iban'],
                    'Valuta': inv['currency'],
                    'Status': '✅'
                }
            else:
                row = {
                    'File': inv['file_name'],
                    'Numero': '',
                    'Data': '',
                    'Fornitore': '',
                    'Cliente': '',
                    'Totale €': 0.00,
                    'Imponibile €': 0.00,
                    'IVA €': 0.00,
                    'Ritenuta €': 0.00,
                    'Scadenza': '',
                    'Metodo Pag.': '',
                    'IBAN': '',
                    'Valuta': '',
                    'Status': f"❌ {inv.get('error_message', 'Errore')}"
                }
            df_data.append(row)
        
        if df_data:
            df = pd.DataFrame(df_data)
            
            # Format monetary columns for display
            display_df = df.copy()
            monetary_cols = ['Totale €', 'Imponibile €', 'IVA €', 'Ritenuta €']
            for col in monetary_cols:
                display_df[col] = display_df[col].apply(lambda x: f"€ {x:,.2f}" if isinstance(x, (int, float)) else x)
            
            # Show dataframe
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Show successful extractions summary
            successful_data = [inv for inv in st.session_state.processed_invoices_simple if inv.get('status') == 'success']
            if successful_data:
                st.success(f"✅ Estratti con successo {len(successful_data)} fatture!")
                
                # Show quick summary
                total_value = sum(inv['total_amount'] for inv in successful_data)
                total_withholding = sum(inv.get('withholding_amount', 0) for inv in successful_data)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"💰 Valore totale fatture: **€ {total_value:,.2f}**")
                with col2:
                    if total_withholding > 0:
                        st.info(f"🏦 Ritenute totali: **€ {total_withholding:,.2f}**")
            
            # Controls
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Cancella Risultati", use_container_width=True):
                    st.session_state.processed_invoices_simple = []
                    st.rerun()
            
            with col2:
                # CSV download
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Scarica CSV",
                    data=csv,
                    file_name=f"fatture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )


# Test the component
if __name__ == "__main__":
    st.set_page_config(page_title="Elaboratore Fatture XML", page_icon="🧾", layout="wide")
    invoice_xml_processor_page()