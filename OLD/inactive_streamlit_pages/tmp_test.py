import streamlit as st
import pandas as pd
from datetime import datetime, date
from decimal import Decimal, getcontext
from typing import Dict, Any, List, Optional, Tuple
import uuid
import toml
from pathlib import Path
from supabase import create_client
import xml.etree.ElementTree as ET

getcontext().prec = 2

# Database connection
@st.cache_resource
def get_supabase_client():
    """Get Supabase client with caching"""
    secrets_path = Path("../../.streamlit/secrets.toml")
    if not secrets_path.exists():
        st.error("Missing .streamlit/secrets.toml file")
        st.stop()

    secrets = toml.load(secrets_path)
    url = secrets.get("SUPABASE_URL")
    key = secrets.get("SUPABASE_ANON_KEY")

    if not url or not key:
        st.error("Missing SUPABASE_URL or SUPABASE_ANON_KEY in secrets.toml")
        st.stop()

    return create_client(url, key)

# Field configuration matching your XML mapping and database schema
FATTURE_EMESSE_FIELDS = {
    'invoice_number': {
        'data_type': 'string',
        'required': True,
        'label': 'Numero Fattura',
        'placeholder': 'es. 2024-001',
        'help': 'Numero identificativo della fattura',
        'xml_tag': 'Numero'
    },
    'document_date': {
        'data_type': 'date',
        'required': True,
        'label': 'Data Documento',
        'help': 'Data di emissione della fattura',
        'xml_tag': 'Data'
    },
    'total_amount': {
        'data_type': 'decimal',
        'required': True,
        'label': 'Importo Totale',
        'help': 'Importo totale della fattura in Euro',
        'xml_tag': 'ImportoTotaleDocumento'
    },
    'due_date': {
        'data_type': 'date',
        'required': False,
        'label': 'Data Scadenza',
        'help': 'Data di scadenza del pagamento',
        'xml_tag': 'DataScadenzaPagamento'
    }
}

# User management
def get_current_user_id():
    """Get current user ID - for now using a test user"""
    # In a real app, this would come from authentication
    return '79cf8633-4faa-46a6-ab79-bf1b53a6101b'

# Helper functions
def get_field_type(fields_config: Dict[str, Any], field_name: str) -> str:
    """Get the data type for a field"""
    return fields_config.get(field_name, {}).get('data_type', 'string')

def is_field_required(fields_config: Dict[str, Any], field_name: str) -> bool:
    """Check if field is required"""
    return fields_config.get(field_name, {}).get('required', False)

def get_field_label(fields_config: Dict[str, Any], field_name: str) -> str:
    """Get display label for field"""
    config = fields_config.get(field_name, {})
    return config.get('label', field_name.replace('_', ' ').title())

def to_decimal(value) -> Decimal:
    """Convert value to Decimal with proper precision"""
    if value is None or value == '':
        return Decimal('0.00')
    try:
        clean_value = str(value).strip().replace(',', '.')
        return Decimal(clean_value)
    except Exception as e:
        raise Exception('Invalid Decimal conversion') from e

def to_italian_date(date_string):
    """Convert date string to datetime object"""
    if not date_string or date_string.strip() == '':
        return None
    return datetime.strptime(date_string.strip(), '%Y-%m-%d')

# Database operations
def fetch_all_records(supabase_client, table_name: str, user_id: str) -> pd.DataFrame:
    """Fetch all records from database for the user"""
    try:
        result = supabase_client.table(table_name).select('*').eq('user_id', user_id).execute()

        if result.data:
            df = pd.DataFrame(result.data)
            # Convert string dates back to date objects for proper handling
            for col in df.columns:
                if col in FATTURE_EMESSE_FIELDS:
                    field_type = get_field_type(FATTURE_EMESSE_FIELDS, col)
                    if field_type == 'date' and not df[col].isna().all():
                        df[col] = pd.to_datetime(df[col]).dt.date
                    elif field_type == 'decimal' and not df[col].isna().all():
                        df[col] = df[col].apply(lambda x: Decimal(str(x)) if pd.notna(x) else Decimal('0.00'))
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Errore nel caricamento dati: {str(e)}")
        return pd.DataFrame()

def save_record_to_database(supabase_client, table_name: str, data: Dict[str, Any]) -> bool:
    """Save new record to database"""
    try:
        # Add required system fields
        data['id'] = str(uuid.uuid4())
        data['user_id'] = get_current_user_id()
        data['created_at'] = datetime.now().isoformat()
        data['updated_at'] = datetime.now().isoformat()

        # Convert data types for database
        processed_data = {}
        for field_name, value in data.items():
            if field_name in FATTURE_EMESSE_FIELDS:
                field_type = get_field_type(FATTURE_EMESSE_FIELDS, field_name)
                if field_type == 'decimal' and value is not None:
                    processed_data[field_name] = float(to_decimal(value))
                elif field_type == 'date' and value is not None:
                    if isinstance(value, date):
                        processed_data[field_name] = value.isoformat()
                    else:
                        processed_data[field_name] = str(value)
                else:
                    processed_data[field_name] = value
            else:
                processed_data[field_name] = value

        result = supabase_client.table(table_name).insert(processed_data).execute()
        return result.data is not None

    except Exception as e:
        st.error(f"Errore nel salvataggio: {str(e)}")
        return False

def update_record_in_database(supabase_client, table_name: str, record_id: str, data: Dict[str, Any]) -> bool:
    """Update existing record in database"""
    try:
        data['updated_at'] = datetime.now().isoformat()

        # Convert data types for database
        processed_data = {}
        for field_name, value in data.items():
            if field_name in FATTURE_EMESSE_FIELDS:
                field_type = get_field_type(FATTURE_EMESSE_FIELDS, field_name)
                if field_type == 'decimal' and value is not None:
                    processed_data[field_name] = float(to_decimal(value))
                elif field_type == 'date' and value is not None:
                    if isinstance(value, date):
                        processed_data[field_name] = value.isoformat()
                    else:
                        processed_data[field_name] = str(value)
                else:
                    processed_data[field_name] = value
            else:
                processed_data[field_name] = value

        result = supabase_client.table(table_name).update(processed_data).eq('id', record_id).execute()
        return result.data is not None

    except Exception as e:
        st.error(f"Errore nell'aggiornamento: {str(e)}")
        return False

def delete_record_from_database(supabase_client, table_name: str, record_id: str) -> bool:
    """Delete record from database"""
    try:
        result = supabase_client.table(table_name).delete().eq('id', record_id).execute()
        return True  # Supabase delete always returns empty data, so we check for no exception

    except Exception as e:
        st.error(f"Errore nell'eliminazione: {str(e)}")
        return False

# UI rendering functions
def render_field_widget(field_name: str, field_config: Dict[str, Any],
                        default_value: Any = None, key_suffix: str = "") -> Any:
    """Render appropriate input widget based on field configuration"""

    field_type = field_config.get('data_type', 'string')
    label = field_config.get('label', field_name.replace('_', ' ').title())
    required = field_config.get('required', False)

    # Add asterisk for required fields
    if required:
        label += " *"

    widget_key = f"{field_name}_{key_suffix}" if key_suffix else field_name
    help_text = field_config.get('help')

    # String fields
    if field_type == 'string':
        widget_type = field_config.get('widget', 'text_input')

        if widget_type == 'textarea':
            return st.text_area(
                label,
                value=default_value or "",
                key=widget_key,
                help=help_text
            )
        elif widget_type == 'selectbox' and field_config.get('options'):
            options = field_config['options']
            index = 0
            if default_value and default_value in options:
                index = options.index(default_value)
            return st.selectbox(
                label,
                options=options,
                index=index,
                key=widget_key,
                help=help_text
            )
        else:
            return st.text_input(
                label,
                value=default_value or "",
                key=widget_key,
                placeholder=field_config.get('placeholder'),
                help=help_text
            )

    # Numeric fields
    elif field_type == 'decimal':
        value = 0.0
        if default_value is not None:
            if isinstance(default_value, Decimal):
                value = float(default_value)
            else:
                value = float(default_value)

        return st.number_input(
            label,
            value=value,
            step=0.01,
            format="%.2f",
            key=widget_key,
            help=help_text
        )

    elif field_type == 'integer':
        return st.number_input(
            label,
            value=int(default_value) if default_value else 0,
            step=1,
            key=widget_key,
            help=help_text
        )

    # Date fields
    elif field_type == 'date':
        if default_value:
            if isinstance(default_value, str):
                default_value = datetime.strptime(default_value, '%Y-%m-%d').date()
            elif isinstance(default_value, datetime):
                default_value = default_value.date()

        return st.date_input(
            label,
            value=default_value or date.today(),
            key=widget_key,
            help=help_text
        )

    # Boolean fields
    elif field_type == 'boolean':
        return st.checkbox(
            label,
            value=bool(default_value) if default_value is not None else False,
            key=widget_key,
            help=help_text
        )

    # Fallback to text input
    else:
        return st.text_input(
            label,
            value=str(default_value) if default_value else "",
            key=widget_key,
            help=help_text
        )

def validate_form_data(fields_config: Dict[str, Any], form_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate form data based on configuration"""
    errors = []

    for field_name, field_config in fields_config.items():
        if field_config.get('required', False):
            value = form_data.get(field_name)
            if not value or (isinstance(value, str) and not value.strip()):
                field_label = get_field_label(fields_config, field_name)
                errors.append(f"Il campo '{field_label}' è obbligatorio")

    return len(errors) == 0, errors

def process_form_data(fields_config: Dict[str, Any], form_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process and convert form data based on field types"""
    processed_data = {}

    for field_name, value in form_data.items():
        if field_name not in fields_config:
            processed_data[field_name] = value
            continue

        field_config = fields_config[field_name]
        field_type = field_config.get('data_type', 'string')

        if field_type == 'decimal' and value is not None:
            processed_data[field_name] = to_decimal(value)
        elif field_type == 'date' and value is not None:
            if isinstance(value, date):
                processed_data[field_name] = value
            else:
                processed_data[field_name] = datetime.strptime(str(value), '%Y-%m-%d').date()
        else:
            processed_data[field_name] = value

    return processed_data

# CRUD UI Components
def render_add_form(supabase_client, table_name: str, fields_config: Dict[str, Any], display_name: str = None) -> None:
    """Render add form for the configured table"""
    display_name = display_name or table_name.replace('_', ' ').title()
    st.subheader(f"➕ Aggiungi {display_name}")

    with st.form(f"add_{table_name}_form"):
        form_data = {}

        # Render fields in columns if many fields
        field_items = list(fields_config.items())

        if len(field_items) > 4:
            # Use columns for better layout
            cols = st.columns(2)
            for i, (field_name, field_config) in enumerate(field_items):
                with cols[i % 2]:
                    form_data[field_name] = render_field_widget(
                        field_name, field_config, key_suffix=f"add_{table_name}"
                    )
        else:
            # Single column layout
            for field_name, field_config in field_items:
                form_data[field_name] = render_field_widget(
                    field_name, field_config, key_suffix=f"add_{table_name}"
                )

        col1, col2 = st.columns([1, 1])

        with col1:
            submitted = st.form_submit_button("💾 Salva", type="primary", use_container_width=True)

        with col2:
            cancelled = st.form_submit_button("🚫 Annulla", use_container_width=True)

        if cancelled:
            st.session_state[f"crud_mode_{table_name}"] = "view"
            st.rerun()

        if submitted:
            # Validate form
            is_valid, errors = validate_form_data(fields_config, form_data)

            if not is_valid:
                for error in errors:
                    st.error(error)
            else:
                # Process and save data
                processed_data = process_form_data(fields_config, form_data)

                if save_record_to_database(supabase_client, table_name, processed_data):
                    st.success("✅ Record salvato con successo!")
                    st.session_state[f"crud_mode_{table_name}"] = "view"
                    # Clear cached data to force refresh
                    if f"{table_name}_cached_data" in st.session_state:
                        del st.session_state[f"{table_name}_cached_data"]
                    st.rerun()
                else:
                    st.error("❌ Errore durante il salvataggio")

def render_data_table(supabase_client, table_name: str, fields_config: Dict[str, Any],
                      display_name: str = None, search_enabled: bool = True) -> Optional[str]:
    """Render data table with optional search and return selected record ID"""
    display_name = display_name or table_name.replace('_', ' ').title()
    st.subheader(f"📋 Visualizza {display_name}")

    # Load data from database
    user_id = get_current_user_id()
    data_df = fetch_all_records(supabase_client, table_name, user_id)

    if data_df.empty:
        st.info(f"Nessun record trovato per {display_name}")
        return None

    # Search functionality
    if search_enabled:
        search_term = st.text_input("🔍 Cerca", placeholder="Digita per cercare...")

        if search_term:
            # Search in all string columns
            string_cols = [col for col in data_df.columns
                           if data_df[col].dtype == 'object' and col not in ['id']]

            if string_cols:
                mask = data_df[string_cols].astype(str).apply(
                    lambda x: x.str.contains(search_term, case=False, na=False)
                ).any(axis=1)
                data_df = data_df[mask]

    # Display table
    if not data_df.empty:
        # Prepare display dataframe (hide system columns)
        display_df = data_df.copy()
        system_cols = ['id', 'created_at', 'updated_at', 'user_id']
        display_df = display_df.drop(columns=[col for col in system_cols if col in display_df.columns])

        # Format columns based on field types
        for col in display_df.columns:
            if col in fields_config:
                field_type = get_field_type(fields_config, col)
                if field_type == 'decimal':
                    display_df[col] = display_df[col].apply(
                        lambda x: f"€ {float(x):,.2f}" if pd.notna(x) else ""
                    )
                elif field_type == 'date':
                    display_df[col] = pd.to_datetime(display_df[col]).dt.strftime('%d/%m/%Y')
                elif field_type == 'boolean':
                    display_df[col] = display_df[col].apply(lambda x: "Sì" if x else "No")

        # Rename columns for display
        display_columns = {}
        for col in display_df.columns:
            if col in fields_config:
                display_columns[col] = get_field_label(fields_config, col)
        display_df = display_df.rename(columns=display_columns)

        # Show table
        st.dataframe(display_df, use_container_width=True)

        # Row selection using selectbox
        if len(data_df) > 0:
            st.write("**Seleziona record per operazioni:**")

            # Create options for selectbox
            options = ["Nessuna selezione"]
            record_map = {}

            for idx, row in data_df.iterrows():
                # Create a readable identifier
                identifier_fields = ['invoice_number', 'name', 'numero', 'cliente']
                identifier = None

                for field in identifier_fields:
                    if field in row and pd.notna(row[field]):
                        identifier = str(row[field])
                        break

                if not identifier:
                    # Fallback to first non-system field
                    for col in row.index:
                        if col not in system_cols and pd.notna(row[col]):
                            identifier = str(row[col])
                            break

                if not identifier:
                    identifier = f"Record {idx}"

                display_text = f"{identifier} (ID: {row['id'][:8]}...)"
                options.append(display_text)
                record_map[display_text] = row['id']

            selected_option = st.selectbox(
                "Scegli record:",
                options=options,
                key=f"select_record_{table_name}"
            )

            if selected_option != "Nessuna selezione":
                return record_map[selected_option]

    return None

def render_modify_form(supabase_client, table_name: str, fields_config: Dict[str, Any],
                       record_id: str, display_name: str = None) -> None:
    """Render modify form for a specific record"""
    display_name = display_name or table_name.replace('_', ' ').title()
    st.subheader(f"✏️ Modifica {display_name}")

    # Get record from database
    user_id = get_current_user_id()
    data_df = fetch_all_records(supabase_client, table_name, user_id)

    if data_df.empty or record_id not in data_df['id'].values:
        st.error("Record non trovato")
        return

    record = data_df[data_df['id'] == record_id].iloc[0].to_dict()

    with st.form(f"modify_{table_name}_form"):
        form_data = {}

        # Render fields with existing values
        field_items = list(fields_config.items())

        if len(field_items) > 4:
            cols = st.columns(2)
            for i, (field_name, field_config) in enumerate(field_items):
                with cols[i % 2]:
                    default_value = record.get(field_name)
                    form_data[field_name] = render_field_widget(
                        field_name, field_config, default_value,
                        key_suffix=f"modify_{table_name}"
                    )
        else:
            for field_name, field_config in field_items:
                default_value = record.get(field_name)
                form_data[field_name] = render_field_widget(
                    field_name, field_config, default_value,
                    key_suffix=f"modify_{table_name}"
                )

        col1, col2 = st.columns([1, 1])

        with col1:
            submitted = st.form_submit_button("💾 Aggiorna", type="primary", use_container_width=True)

        with col2:
            cancelled = st.form_submit_button("🚫 Annulla", use_container_width=True)

        if cancelled:
            st.session_state[f"crud_mode_{table_name}"] = "view"
            st.rerun()

        if submitted:
            # Validate form
            is_valid, errors = validate_form_data(fields_config, form_data)

            if not is_valid:
                for error in errors:
                    st.error(error)
            else:
                # Process and update data
                processed_data = process_form_data(fields_config, form_data)

                if update_record_in_database(supabase_client, table_name, record_id, processed_data):
                    st.success("✅ Record aggiornato con successo!")
                    st.session_state[f"crud_mode_{table_name}"] = "view"
                    # Clear cached data to force refresh
                    if f"{table_name}_cached_data" in st.session_state:
                        del st.session_state[f"{table_name}_cached_data"]
                    st.rerun()
                else:
                    st.error("❌ Errore durante l'aggiornamento")

def render_delete_confirmation(supabase_client, table_name: str, fields_config: Dict[str, Any],
                               record_id: str, display_name: str = None) -> None:
    """Render delete confirmation dialog"""
    display_name = display_name or table_name.replace('_', ' ').title()
    st.subheader(f"🗑️ Elimina {display_name}")

    # Get record from database
    user_id = get_current_user_id()
    data_df = fetch_all_records(supabase_client, table_name, user_id)

    if data_df.empty or record_id not in data_df['id'].values:
        st.error("Record non trovato")
        return

    record = data_df[data_df['id'] == record_id].iloc[0].to_dict()

    st.warning("⚠️ Sei sicuro di voler eliminare questo record? L'operazione non può essere annullata.")

    # Show record details
    with st.expander("👁️ Visualizza dettagli record"):
        for field_name, field_config in fields_config.items():
            field_label = get_field_label(fields_config, field_name)
            field_value = record.get(field_name, "")

            # Format value based on type
            field_type = get_field_type(fields_config, field_name)
            if field_type == 'decimal' and field_value:
                field_value = f"€ {float(field_value):,.2f}"
            elif field_type == 'date' and field_value:
                if isinstance(field_value, (date, datetime)):
                    field_value = field_value.strftime('%d/%m/%Y')
            elif field_type == 'boolean':
                field_value = "Sì" if field_value else "No"

            st.write(f"**{field_label}:** {field_value}")

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("🗑️ Conferma Eliminazione", type="primary", use_container_width=True):
            if delete_record_from_database(supabase_client, table_name, record_id):
                st.success("✅ Record eliminato con successo!")
                st.session_state[f"crud_mode_{table_name}"] = "view"
                # Clear cached data to force refresh
                if f"{table_name}_cached_data" in st.session_state:
                    del st.session_state[f"{table_name}_cached_data"]
                st.rerun()
            else:
                st.error("❌ Errore durante l'eliminazione")

    with col2:
        if st.button("🚫 Annulla", use_container_width=True):
            st.session_state[f"crud_mode_{table_name}"] = "view"
            st.rerun()

def render_crud_interface(supabase_client, table_name: str, fields_config: Dict[str, Any],
                          display_name: str = None) -> None:
    """Render complete CRUD interface"""
    display_name = display_name or table_name.replace('_', ' ').title()

    # Operation buttons
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button(f"➕ Aggiungi", use_container_width=True):
            st.session_state[f"crud_mode_{table_name}"] = "add"

    with col2:
        if st.button("📋 Visualizza", use_container_width=True):
            st.session_state[f"crud_mode_{table_name}"] = "view"

    with col3:
        if st.button("✏️ Modifica", use_container_width=True):
            st.session_state[f"crud_mode_{table_name}"] = "modify"

    with col4:
        if st.button("🗑️ Elimina", use_container_width=True):
            st.session_state[f"crud_mode_{table_name}"] = "delete"

    st.write("---")

    # Initialize mode if not set
    mode_key = f"crud_mode_{table_name}"
    if mode_key not in st.session_state:
        st.session_state[mode_key] = "view"

    current_mode = st.session_state[mode_key]

    if current_mode == "add":
        render_add_form(supabase_client, table_name, fields_config, display_name)

    elif current_mode == "view":
        render_data_table(supabase_client, table_name, fields_config, display_name)

    elif current_mode == "modify":
        selected_id = render_data_table(supabase_client, table_name, fields_config, display_name, search_enabled=False)
        if selected_id:
            st.write("---")
            render_modify_form(supabase_client, table_name, fields_config, selected_id, display_name)
        else:
            st.info("👆 Seleziona un record dalla tabella per modificarlo")

    elif current_mode == "delete":
        selected_id = render_data_table(supabase_client, table_name, fields_config, display_name, search_enabled=False)
        if selected_id:
            st.write("---")
            render_delete_confirmation(supabase_client, table_name, fields_config, selected_id, display_name)
        else:
            st.info("👆 Seleziona un record dalla tabella per eliminarlo")

# XML Processing Integration
def process_xml_files_for_import(xml_files, field_mapping):
    """Process XML files and extract data for database import"""
    results = []

    for xml_file in xml_files:
        try:
            # Parse XML
            xml_content = xml_file.read()
            xml_tree = ET.fromstring(xml_content)

            extracted_data = {}

            # Extract data based on field mapping
            for field_name, field_config in field_mapping.items():
                xml_tag = field_config.get('xml_tag')
                if xml_tag:
                    # Find element by tag name (simplified version)
                    element = xml_tree.find(f".//{xml_tag}")
                    if element is not None and element.text:
                        value = element.text.strip()

                        # Apply basic data type conversion
                        field_type = field_config.get('data_type', 'string')
                        if field_type == 'date' and value:
                            try:
                                # Convert from XML date format to Python date
                                extracted_data[field_name] = datetime.strptime(value, '%Y-%m-%d').date()
                            except ValueError:
                                st.warning(f"Invalid date format in {xml_file.name}: {value}")
                                extracted_data[field_name] = None
                        elif field_type == 'decimal' and value:
                            try:
                                # Handle European decimal format
                                clean_value = value.replace(',', '.')
                                extracted_data[field_name] = to_decimal(clean_value)
                            except:
                                st.warning(f"Invalid decimal format in {xml_file.name}: {value}")
                                extracted_data[field_name] = Decimal('0.00')
                        else:
                            extracted_data[field_name] = value
                    else:
                        # Handle missing optional fields
                        if field_config.get('required', False):
                            raise Exception(f"Required field {field_name} not found in XML")
                        else:
                            extracted_data[field_name] = None

            results.append({
                'filename': xml_file.name,
                'data': extracted_data,
                'status': 'success'
            })

        except Exception as e:
            results.append({
                'filename': xml_file.name,
                'data': {},
                'status': 'error',
                'error': str(e)
            })

    return results

def render_xml_upload_section(supabase_client, table_name: str, fields_config: Dict[str, Any]):
    """Render XML file upload and processing section"""
    st.subheader("📄 Caricamento Fatture XML")

    uploaded_files = st.file_uploader(
        "Trascina qui le tue fatture in formato XML o clicca per selezionare",
        type=['xml'],
        accept_multiple_files=True,
        help="Carica fino a 20 fatture XML contemporaneamente"
    )

    if uploaded_files:
        st.success(f"📄 {len(uploaded_files)} file caricato/i con successo!")

        # Display uploaded files info
        with st.expander("📋 File caricati", expanded=True):
            for i, file in enumerate(uploaded_files, 1):
                st.write(f"**{i}.** {file.name} ({file.size} bytes)")

        # Process button
        col1, col2 = st.columns([1, 3])

        with col1:
            process_button = st.button("🔄 Elabora Fatture", type="primary", use_container_width=True)

        with col2:
            if st.button("❌ Cancella", use_container_width=True):
                st.rerun()

        if process_button:
            with st.spinner("Elaborazione XML in corso..."):
                # Process XML files
                results = process_xml_files_for_import(uploaded_files, fields_config)

                # Show processing results
                successful_results = [r for r in results if r['status'] == 'success']
                error_results = [r for r in results if r['status'] == 'error']

                st.write("---")
                st.subheader("📊 Risultati Elaborazione")

                # Summary metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Totale File", len(results))
                with col2:
                    st.metric("Elaborati", len(successful_results), delta=f"+{len(successful_results)}")
                with col3:
                    st.metric("Errori", len(error_results), delta=f"+{len(error_results)}" if error_results else None)

                # Show errors if any
                if error_results:
                    st.error("⚠️ Alcuni file presentano errori:")
                    for error_result in error_results:
                        st.write(f"❌ **{error_result['filename']}**: {error_result['error']}")

                # Show successful results for preview
                if successful_results:
                    st.success("✅ File elaborati con successo:")

                    # Create preview dataframe
                    preview_data = []
                    for result in successful_results:
                        row = result['data'].copy()
                        row['filename'] = result['filename']
                        preview_data.append(row)

                    preview_df = pd.DataFrame(preview_data)

                    # Format preview data for display
                    display_df = preview_df.copy()
                    for col in display_df.columns:
                        if col in fields_config:
                            field_type = get_field_type(fields_config, col)
                            if field_type == 'decimal':
                                display_df[col] = display_df[col].apply(
                                    lambda x: f"€ {float(x):,.2f}" if pd.notna(x) and x != '' else ""
                                )
                            elif field_type == 'date':
                                display_df[col] = pd.to_datetime(display_df[col], errors='coerce').dt.strftime('%d/%m/%Y')

                    # Rename columns for display
                    display_columns = {'filename': 'Nome File'}
                    for col in display_df.columns:
                        if col in fields_config:
                            display_columns[col] = get_field_label(fields_config, col)

                    display_df = display_df.rename(columns=display_columns)
                    st.dataframe(display_df, use_container_width=True)

                    # Confirmation to save to database
                    st.write("---")
                    st.subheader("💾 Salvataggio nel Database")

                    col1, col2 = st.columns([1, 1])

                    with col1:
                        if st.button("✅ Conferma e Salva nel Database", type="primary", use_container_width=True):
                            saved_count = 0
                            errors = []

                            for result in successful_results:
                                if save_record_to_database(supabase_client, table_name, result['data']):
                                    saved_count += 1
                                else:
                                    errors.append(f"Errore salvando {result['filename']}")

                            if errors:
                                for error in errors:
                                    st.error(error)

                            st.success(f"🎉 {saved_count} fatture salvate con successo nel database!")

                            # Clear cached data to force refresh
                            if f"{table_name}_cached_data" in st.session_state:
                                del st.session_state[f"{table_name}_cached_data"]

                            # Auto-switch to view mode
                            st.session_state[f"crud_mode_{table_name}"] = "view"

                            # Clear the uploader
                            time.sleep(2)  # Give user time to see success message
                            st.rerun()

                    with col2:
                        if st.button("❌ Annulla", use_container_width=True):
                            st.rerun()

def render_export_section(supabase_client, table_name: str, fields_config: Dict[str, Any]):
    """Render data export section"""
    st.subheader("📤 Esporta Dati")

    user_id = get_current_user_id()
    data_df = fetch_all_records(supabase_client, table_name, user_id)

    if data_df.empty:
        st.info("Nessun dato da esportare")
        return

    st.write(f"**Totale record disponibili:** {len(data_df)}")

    # Export options
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📊 Scarica CSV", use_container_width=True):
            # Prepare export dataframe
            export_df = data_df.copy()

            # Remove system columns
            system_cols = ['id', 'user_id', 'created_at', 'updated_at']
            export_df = export_df.drop(columns=[col for col in system_cols if col in export_df.columns])

            # Rename columns
            display_columns = {}
            for col in export_df.columns:
                if col in fields_config:
                    display_columns[col] = get_field_label(fields_config, col)
            export_df = export_df.rename(columns=display_columns)

            csv = export_df.to_csv(index=False)
            st.download_button(
                label="⬇️ Download CSV",
                data=csv,
                file_name=f"{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )

    with col2:
        if st.button("📋 Copia negli Appunti", use_container_width=True):
            st.info("Funzionalità non ancora implementata")

# Main Application
def fatture_emesse_app():
    """Main application for Fatture Emesse management"""
    st.set_page_config(
        page_title="Gestione Fatture Emesse",
        page_icon="🧾",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Get Supabase client
    supabase_client = get_supabase_client()

    # Header
    st.title("🧾 Gestione Fatture Emesse")
    st.write("Sistema integrato per la gestione delle fatture con supporto XML e database")

    # Sidebar with statistics and quick actions
    with st.sidebar:
        st.header("📊 Statistiche")

        user_id = get_current_user_id()
        data_df = fetch_all_records(supabase_client, "fatture_emesse", user_id)

        if not data_df.empty:
            # Quick stats
            total_count = len(data_df)
            total_amount = data_df['total_amount'].sum() if 'total_amount' in data_df.columns else 0

            st.metric("Totale Fatture", total_count)
            st.metric("Importo Totale", f"€ {float(total_amount):,.2f}")

            # Recent activity
            if 'created_at' in data_df.columns:
                recent_df = data_df.sort_values('created_at', ascending=False).head(3)
                st.subheader("🕒 Ultime Fatture")
                for _, row in recent_df.iterrows():
                    st.write(f"• {row.get('invoice_number', 'N/A')} - €{float(row.get('total_amount', 0)):,.2f}")
        else:
            st.info("Nessuna fattura ancora presente")

        st.write("---")

        # Quick actions
        st.subheader("⚡ Azioni Rapide")

        if st.button("➕ Nuova Fattura", use_container_width=True):
            st.session_state["crud_mode_fatture_emesse"] = "add"
            st.rerun()

        if st.button("📄 Carica XML", use_container_width=True):
            st.session_state["show_xml_upload"] = True
            st.rerun()

        if st.button("📤 Esporta", use_container_width=True):
            st.session_state["show_export"] = True
            st.rerun()

    # Main content area with tabs
    tab1, tab2, tab3 = st.tabs(["📋 Gestione CRUD", "📄 Caricamento XML", "📤 Esportazione"])

    with tab1:
        st.subheader("Operazioni CRUD")
        render_crud_interface(supabase_client, "fatture_emesse", FATTURE_EMESSE_FIELDS, "Fattura")

    with tab2:
        render_xml_upload_section(supabase_client, "fatture_emesse", FATTURE_EMESSE_FIELDS)

    with tab3:
        render_export_section(supabase_client, "fatture_emesse", FATTURE_EMESSE_FIELDS)

    # Footer with additional info
    st.write("---")
    st.caption("💡 **Suggerimento:** Usa la funzione di caricamento XML per importare automaticamente le fatture elettroniche")

# Advanced features
def render_bulk_operations(supabase_client, table_name: str, fields_config: Dict[str, Any]):
    """Render bulk operations interface"""
    st.subheader("🔧 Operazioni Multiple")

    user_id = get_current_user_id()
    data_df = fetch_all_records(supabase_client, table_name, user_id)

    if data_df.empty:
        st.info("Nessun dato disponibile per operazioni multiple")
        return

    # Bulk delete by criteria
    st.write("**Eliminazione multipla per criteri:**")

    col1, col2, col3 = st.columns(3)

    with col1:
        field_to_filter = st.selectbox(
            "Campo da filtrare:",
            options=list(fields_config.keys()),
            format_func=lambda x: get_field_label(fields_config, x)
        )

    with col2:
        if get_field_type(fields_config, field_to_filter) == 'string':
            filter_value = st.text_input("Valore:")
        elif get_field_type(fields_config, field_to_filter) == 'decimal':
            filter_value = st.number_input("Valore:", step=0.01)
        elif get_field_type(fields_config, field_to_filter) == 'date':
            filter_value = st.date_input("Valore:")
        else:
            filter_value = st.text_input("Valore:")

    with col3:
        st.write("")  # Spacing
        st.write("")  # Spacing
        if st.button("🗑️ Elimina per Criterio", type="secondary"):
            if filter_value:
                # Find matching records
                if get_field_type(fields_config, field_to_filter) == 'string':
                    mask = data_df[field_to_filter].astype(str).str.contains(str(filter_value), case=False, na=False)
                else:
                    mask = data_df[field_to_filter] == filter_value

                matching_records = data_df[mask]

                if not matching_records.empty:
                    st.warning(f"⚠️ Trovati {len(matching_records)} record corrispondenti. Confermi l'eliminazione?")

                    col_confirm, col_cancel = st.columns(2)

                    with col_confirm:
                        if st.button("✅ Conferma Eliminazione", type="primary"):
                            deleted_count = 0
                            for record_id in matching_records['id']:
                                if delete_record_from_database(supabase_client, table_name, record_id):
                                    deleted_count += 1

                            st.success(f"✅ {deleted_count} record eliminati con successo!")
                            st.rerun()

                    with col_cancel:
                        if st.button("❌ Annulla"):
                            st.rerun()
                else:
                    st.info("Nessun record trovato con i criteri specificati")

def render_data_validation_report(supabase_client, table_name: str, fields_config: Dict[str, Any]):
    """Render data validation and quality report"""
    st.subheader("📋 Report Qualità Dati")

    user_id = get_current_user_id()
    data_df = fetch_all_records(supabase_client, table_name, user_id)

    if data_df.empty:
        st.info("Nessun dato da analizzare")
        return

    # Data quality metrics
    st.write("**Metriche di Qualità:**")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Record Totali", len(data_df))

    with col2:
        # Count records with all required fields filled
        complete_records = 0
        for _, row in data_df.iterrows():
            is_complete = True
            for field_name, field_config in fields_config.items():
                if field_config.get('required', False):
                    if pd.isna(row.get(field_name)) or row.get(field_name) == '':
                        is_complete = False
                        break
            if is_complete:
                complete_records += 1

        st.metric("Record Completi", complete_records)

    with col3:
        # Count duplicate invoice numbers
        duplicates = 0
        if 'invoice_number' in data_df.columns:
            duplicates = data_df['invoice_number'].duplicated().sum()
        st.metric("Duplicati", duplicates)

    with col4:
        # Count records with future dates
        future_dates = 0
        if 'document_date' in data_df.columns:
            today = date.today()
            future_dates = (pd.to_datetime(data_df['document_date']).dt.date > today).sum()
        st.metric("Date Future", future_dates)

    # Detailed validation issues
    if st.checkbox("Mostra dettagli problemi qualità"):
        issues = []

        for idx, row in data_df.iterrows():
            row_issues = []

            # Check required fields
            for field_name, field_config in fields_config.items():
                if field_config.get('required', False):
                    if pd.isna(row.get(field_name)) or row.get(field_name) == '':
                        row_issues.append(f"Campo obbligatorio '{get_field_label(fields_config, field_name)}' mancante")

            # Check future dates
            if 'document_date' in row and pd.notna(row['document_date']):
                doc_date = pd.to_datetime(row['document_date']).date()
                if doc_date > date.today():
                    row_issues.append("Data documento nel futuro")

            # Check negative amounts
            if 'total_amount' in row and pd.notna(row['total_amount']):
                if float(row['total_amount']) < 0:
                    row_issues.append("Importo negativo")

            if row_issues:
                issues.append({
                    'Record': row.get('invoice_number', f"ID: {row.get('id', 'N/A')[:8]}..."),
                    'Problemi': '; '.join(row_issues)
                })

        if issues:
            issues_df = pd.DataFrame(issues)
            st.dataframe(issues_df, use_container_width=True)
        else:
            st.success("✅ Nessun problema di qualità rilevato!")

# Entry point
if __name__ == "__main__":
    # Add missing import for time
    import time

    fatture_emesse_app()