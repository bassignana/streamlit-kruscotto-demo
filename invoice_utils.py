import time

import streamlit as st
import pandas as pd
from datetime import datetime, date
from decimal import Decimal
from invoice_xml_processor import process_xml_list

def render_add_form(supabase_client, table_name, fields_config, display_name = None):
    display_name = display_name or table_name.replace('_', ' ').title()
    st.subheader(f"Aggiungi {display_name}")

    with st.form(f"add_{table_name}_form",
                 clear_on_submit=True,
                 enter_to_submit=False):

        form_data = {}
        field_items = list(fields_config.items())


        # Render fields in columns if many fields
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
            st.rerun()

        if submitted:
            try:
                is_valid, errors = validate_required_form_data(fields_config, form_data)

                if not is_valid:
                    for error in errors:
                        st.error(error)
                else:
                    processed_data = {}
                    processed_data['user_id'] = st.session_state['user']['id']
                    # todo: the correct thing should be creating
                    # default values for all non required fields,
                    # that is consistent throughout all fields and
                    # compatible with a direct upload to the database.
                    # Maybe a string, for sure not None.
                    #
                    # For now I'm just uploading the str() version of whatever
                    # value I get from form_data and dropping non required fields
                    for field_name, field_config in fields_config.items():
                        if field_config.get('required', False):
                            value = form_data.get(field_name)
                            # for field_name, value in form_data.items():
                            processed_data[field_name] = str(value)

                    # Correct format to use for save_to_database()
                    # todo: now that I don't use save_to_database() anymore
                    # do I have to keep this format?
                    data_to_upload = {}
                    data_to_upload['data'] = processed_data
                    data_to_upload['status'] = 'success'
                    list_data = []
                    list_data.append(data_to_upload)
                    print(list_data)

                    with st.spinner("Salvataggio in corso..."):
                        successful_results = [r.get('data') for r in list_data if r['status'] == 'success']

                        try:
                            result = supabase_client.table(table_name).insert(successful_results).execute()
                            print("Insert successful:", result.data)
                            st.success("Fattura salvata con successo nel database!")
                            time.sleep(2)
                            # todo: for resetting fields on reload I have to delete these
                            # keys in the session state, or understand where they are formed
                            # and clean them up some other way.
                            # "numero_fattura_add_fatture_emesse":"1"
                            # "partita_iva_prestatore_add_fatture_emesse":"1"
                            # "data_scadenza_pagamento_add_fatture_emesse":NULL
                            # "data_documento_add_fatture_emesse":"datetime.date(2025, 7, 31)"
                            st.rerun()
                        except Exception as e:
                            st.error("Error inserting data:", e)

            except Exception as e:
                print(f'Error adding invoice manually: {e}')

def to_decimal(value) -> Decimal:
    """Convert value to Decimal with proper precision"""
    if value is None or value == '':
        return Decimal('0.00')
    try:
        clean_value = str(value).strip().replace(',', '.')
        return Decimal(clean_value)
    except Exception as e:
        raise Exception('Invalid Decimal conversion') from e

def render_field_widget(field_name, field_config, default_value = None, key_suffix = ""):
    """Render appropriate SINGLE input widget based on field configuration"""

    field_type = field_config.get('data_type', 'string')
    label = field_config.get('label', field_name.replace('_', ' ').title())
    widget_key = f"{field_name}_{key_suffix}" if key_suffix else field_name
    help_text = field_config.get('help')
    required = field_config.get('required', False)

    # Add asterisk for required fields
    if required:
        label += " *"

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
        value = 0.00
        if default_value is not None:
            if isinstance(default_value, Decimal):
                value = float(default_value)
            else:
                value = float(default_value)

        return st.number_input(
            label,
            value=value,
            step=1.00,
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

        if required:
            return st.date_input(
                label,
                value=default_value or date.today(),
                key=widget_key,
                help=help_text
            )
        else:
            return st.date_input(
                value = None,
                label = label,
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

def validate_required_form_data(fields_config, form_data):
    """Validate form data based on configuration"""
    errors = []

    for field_name, field_config in fields_config.items():
        if field_config.get('required', False):
            value = form_data.get(field_name)
            if not value or (isinstance(value, str) and not value.strip()):
                field_label = fields_config.get('label', field_name.replace('_', ' ').title())
                errors.append(f"Il campo '{field_label}' è obbligatorio")

    return len(errors) == 0, errors

def process_form_data(fields_config, form_data):
    """Process and convert form data FOR THE UPLOAD based on field types"""
    # todo: what formatting to use? because of errors like
    # Error inserting data: Object of type date is not JSON serializable
    # maybe I can just upload strings?

    processed_data = {}

    for field_name, value in form_data.items():
        # if field_name not in fields_config:
        #     processed_data[field_name] = value
        #     continue
        #
        # field_config = fields_config[field_name]
        # field_type = field_config.get('data_type', 'string')
        #
        # if field_type == 'decimal' and value is not None:
        #     processed_data[field_name] = to_decimal(value)
        # elif field_type == 'date' and value is not None:
        #     if isinstance(value, date):
        #         processed_data[field_name] = value
        #     else:
        #         processed_data[field_name] = datetime.strptime(str(value), '%Y-%m-%d').date()
        # else:
        #     processed_data[field_name] = value
        processed_data[field_name] = str(value)

    return processed_data

def fetch_all_records(supabase_client, table_name: str, user_id: str):
    """Fetch all records from database for the user"""
    try:
        result = supabase_client.table(table_name).select('*').eq('user_id', user_id).execute()

        if result.data:
            df = pd.DataFrame(result.data)
            # Convert string dates back to date objects for proper handling
            # for col in df.columns:
            #     if col in FATTURE_EMESSE_FIELDS:
            #         field_type = get_field_type(FATTURE_EMESSE_FIELDS, col)
            #         if field_type == 'date' and not df[col].isna().all():
            #             df[col] = pd.to_datetime(df[col]).dt.date
            #         elif field_type == 'decimal' and not df[col].isna().all():
            #             df[col] = df[col].apply(lambda x: Decimal(str(x)) if pd.notna(x) else Decimal('0.00'))
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Errore nel caricamento dati: {str(e)}")
        return pd.DataFrame()

def update_record_in_database(supabase_client, table_name: str, record_id: str, data):
    """Update existing record in database"""
    try:
        data['updated_at'] = datetime.now().isoformat()

        # Convert data types for database
        processed_data = {}
        for field_name, value in data.items():
            # if field_name in FATTURE_EMESSE_FIELDS:
            #     field_type = get_field_type(FATTURE_EMESSE_FIELDS, field_name)
            #     if field_type == 'decimal' and value is not None:
            #         processed_data[field_name] = float(to_decimal(value))
            #     elif field_type == 'date' and value is not None:
            #         if isinstance(value, date):
            #             processed_data[field_name] = value.isoformat()
            #         else:
            #             processed_data[field_name] = str(value)
            #     else:
            #         processed_data[field_name] = value
            # else:
            #     processed_data[field_name] = value
            processed_data[field_name] = str(value)

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

def render_xml_upload_section(supabase_client, table_name, fields_config, display_name):
    """Render XML file upload and processing section"""
    st.subheader(f"Caricamento XML {display_name}")

    # Initialize session state for XML processing
    if 'xml_processing_results' not in st.session_state:
        st.session_state.xml_processing_results = None
    if 'xml_processing_stage' not in st.session_state:
        st.session_state.xml_processing_stage = 'upload'  # upload -> processed -> saved

    uploaded_files = st.file_uploader(
        "Trascina qui le tue fatture in formato XML o clicca per selezionare",
        type=['xml'],
        accept_multiple_files=True,
        help="Carica fino a 20 fatture XML contemporaneamente"
    )

    if uploaded_files:
        st.success(f"📄 {len(uploaded_files)} file pronti per il caricamento.")

        # Display uploaded files info
        with st.expander("📋 File da elaborare", expanded=True):
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
                # Process XML files and store in session state
                results = process_xml_list(uploaded_files)
                st.session_state.xml_processing_results = results
                st.session_state.xml_processing_stage = 'processed'
                st.rerun()  # Rerun to show results

        if st.session_state.xml_processing_results and st.session_state.xml_processing_stage == 'processed':
            results = st.session_state.xml_processing_results

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
                # for error_result in error_results:
                #     st.write(f"❌ **{error_result['filename']}**: {error_result['error']}")

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
                # for col in display_df.columns:
                #     if col in fields_config:
                #         field_type = get_field_type(fields_config, col)
                #         if field_type == 'decimal':
                #             display_df[col] = display_df[col].apply(
                #                 lambda x: f"€ {float(x):,.2f}" if pd.notna(x) and x != '' else ""
                #             )
                #         elif field_type == 'date':
                #             display_df[col] = pd.to_datetime(display_df[col], errors='coerce').dt.strftime('%d/%m/%Y')
                #
                # # Rename columns for display
                # display_columns = {'filename': 'Nome File'}
                # for col in display_df.columns:
                #     if col in fields_config:
                #         display_columns[col] = get_field_label(fields_config, col)
                #
                # display_df = display_df.rename(columns=display_columns)
                st.dataframe(display_df, use_container_width=True)

                # Confirmation to save to database
                st.write("---")
                st.subheader("💾 Salvataggio nel Database")

                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("✅ Conferma e Salva nel Database", type="primary", use_container_width=True):
                        with st.spinner("Salvataggio in corso..."):
                            try:

                                # Data preprocessing before insert in DB
                                # Copying data in case I'll use successful_results for visualization.
                                data_to_insert = [ r['data'] for r in successful_results]
                                for data in data_to_insert:
                                    # With postgres triggers, created_at and updated_at should be
                                    # automatically updated by the database.
                                    # data['data']['created_at'] = datetime.now().isoformat()
                                    # data['data']['updated_at'] = datetime.now().isoformat()
                                    data['user_id'] = st.session_state['user']['id']

                                result = supabase_client.table(table_name).insert(data_to_insert).execute()
                                print("Insert successful:", result.data)
                                st.success("Fatture salvate con successo nel database!")

                                # Clear session state after successful save
                                st.session_state.xml_processing_results = None
                                st.session_state.xml_processing_stage = 'saved'

                                time.sleep(2)
                                st.rerun()

                            except Exception as e:
                                st.error(f"❌ Errore durante il salvataggio: {str(e)}")
                                print(f"Save error: {str(e)}")
                                raise

                with col2:
                    if st.button("❌ Annulla", use_container_width=True):
                        st.rerun()

def render_modify_form(supabase_client, user_id, table_name, fields_config, record_id, display_name = None):
    """Render modify form for a specific record"""
    display_name = display_name or table_name.replace('_', ' ').title()
    # st.subheader(f"✏️ Modifica {display_name}")

    # Get record from database
    data_df = fetch_all_records(supabase_client, table_name, user_id)

    if data_df.empty or record_id not in data_df['id'].values:
        st.error("Nessuna fattura trovata")
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
            st.rerun()

        if submitted:
            try:
                is_valid, errors = validate_required_form_data(fields_config, form_data)

                if not is_valid:
                    for error in errors:
                        st.error(error)
                else:
                    processed_data = {}
                    processed_data['user_id'] = st.session_state['user']['id']
                    for field_name, field_config in fields_config.items():
                        if field_config.get('required', False):
                            value = form_data.get(field_name)
                            processed_data[field_name] = str(value)

                    with st.spinner("Salvataggio in corso..."):
                        result = supabase_client.table(table_name).update(processed_data).eq('id', record_id).execute()
                        if result:
                            st.success("Fattura salvata con successo nel database!")
                            time.sleep(2)
                            st.rerun()
            except Exception as e:
                print(f'Error updating invoice: {e}')
                raise

def render_data_table(supabase_client, user_id, table_name, fields_config, display_name = None, search_enabled = True):
    """Render data table with optional search and return selected record ID"""
    display_name = display_name or table_name.replace('_', ' ').title()

    # Load data from database
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
        # for col in display_df.columns:
        #     if col in fields_config:
        #         field_type = get_field_type(fields_config, col)
        #         if field_type == 'decimal':
        #             display_df[col] = display_df[col].apply(
        #                 lambda x: f"€ {float(x):,.2f}" if pd.notna(x) else ""
        #             )
        #         elif field_type == 'date':
        #             display_df[col] = pd.to_datetime(display_df[col]).dt.strftime('%d/%m/%Y')
        #         elif field_type == 'boolean':
        #             display_df[col] = display_df[col].apply(lambda x: "Sì" if x else "No")

        # Rename columns for display
        # display_columns = {}
        # for col in display_df.columns:
        #     if col in fields_config:
        #         display_columns[col] = get_field_label(fields_config, col)
        # display_df = display_df.rename(columns=display_columns)

        # Show table
        st.write('Fatture disponibili:')
        st.dataframe(display_df, use_container_width=True)

        # Row selection using selectbox
        if len(data_df) > 0:

            # Create options for selectbox
            options = ["Nessuna selezione"]
            record_map = {}

            for idx, row in data_df.iterrows():
                # Create a readable identifier
                identifier_fields = ['numero_fattura', 'name', 'numero', 'cliente']
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
                "Clicca o digita per selezionare una fattura:",
                options=options,
                key=f"select_record_{table_name}"
            )

            if selected_option != "Nessuna selezione":
                return record_map[selected_option]

    return None

def render_delete_confirmation(supabase_client, user_id, table_name, fields_config, record_id, display_name = None):
    """Render delete confirmation dialog"""
    display_name = display_name or table_name.replace('_', ' ').title()

    # Get record from database
    data_df = fetch_all_records(supabase_client, table_name, user_id)

    if data_df.empty or record_id not in data_df['id'].values:
        st.error("Record non trovato")
        return

    record = data_df[data_df['id'] == record_id].iloc[0].to_dict()

    st.warning("Sei sicuro di voler eliminare questa fattura? L'operazione non può essere annullata.")

    # Show record details
    with st.expander("Visualizza dettagli fattura"):
        for field_name, field_config in fields_config.items():
            field_label = get_field_label(fields_config, field_name)
            field_value = record.get(field_name, "")

            # Format value based on type
            field_type = fields_config.get(field_name, {}).get('data_type', 'string')
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
        if st.button("Conferma Eliminazione", type="primary", use_container_width=True):
            try:

                with st.spinner("Salvataggio in corso..."):
                    # todo: check this.
                    # Supabase delete always returns empty data, so we check for no exception
                    result = supabase_client.table(table_name).delete().eq('id', record_id).execute()
                    if result:
                        st.success("Fattura eliminata con successo dal database!")
                        time.sleep(2)
                        st.rerun()
            except Exception as e:
                print(f'Error deleting fattura: {e}')
                raise

    with col2:
        if st.button("🚫 Annulla", use_container_width=True):
            st.session_state[f"crud_mode_{table_name}"] = "view"
            st.rerun()

def get_field_label(fields_config, field_name):
    """Get display label for field"""
    config = fields_config.get(field_name, {})
    return config.get('label', field_name.replace('_', ' ').title())

def render_generic_xml_upload_section(supabase_client, table_name, fields_config, display_name):
    """Render XML file upload and processing section"""
    st.subheader(f"Caricamento fatture formato XML")

    if 'xml_processing_results' not in st.session_state:
        st.session_state.xml_processing_results = None
    if 'xml_processing_stage' not in st.session_state:
        st.session_state.xml_processing_stage = 'upload'  # upload -> processed -> saved

    uploaded_files = st.file_uploader(
        "Trascina qui le tue fatture in formato XML o clicca per selezionare",
        type=['xml'],
        accept_multiple_files=True,
        help="Carica fino a 20 fatture XML contemporaneamente"
    )

    if uploaded_files:
        st.success(f"{len(uploaded_files)} file pronti per il caricamento.")

        with st.expander("📋 File da elaborare", expanded=True):
            for i, file in enumerate(uploaded_files, 1):
                st.write(f"**{i}.** {file.name} ({file.size} bytes)")

        col1, col2 = st.columns([1, 3])

        with col1:
            process_button = st.button("Elabora Fatture", type="primary", use_container_width=True)

        with col2:
            if st.button("Annulla", use_container_width=True):
                st.rerun()

        if process_button:
            with st.spinner("Elaborazione XML in corso..."):
                results = process_xml_list(uploaded_files)
                st.session_state.xml_processing_results = results
                st.session_state.xml_processing_stage = 'processed'
                st.rerun()  # Rerun to show results

        if st.session_state.xml_processing_results and st.session_state.xml_processing_stage == 'processed':
            results = st.session_state.xml_processing_results

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
                # for error_result in error_results:
                #     st.write(f"❌ **{error_result['filename']}**: {error_result['error']}")

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
                # for col in display_df.columns:
                #     if col in fields_config:
                #         field_type = get_field_type(fields_config, col)
                #         if field_type == 'decimal':
                #             display_df[col] = display_df[col].apply(
                #                 lambda x: f"€ {float(x):,.2f}" if pd.notna(x) and x != '' else ""
                #             )
                #         elif field_type == 'date':
                #             display_df[col] = pd.to_datetime(display_df[col], errors='coerce').dt.strftime('%d/%m/%Y')
                #
                # # Rename columns for display
                # display_columns = {'filename': 'Nome File'}
                # for col in display_df.columns:
                #     if col in fields_config:
                #         display_columns[col] = get_field_label(fields_config, col)
                #
                # display_df = display_df.rename(columns=display_columns)
                st.dataframe(display_df, use_container_width=True)

                # Confirmation to save to database
                st.write("---")
                st.subheader("💾 Salvataggio nel Database")

                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("✅ Conferma e Salva nel Database", type="primary", use_container_width=True):
                        with st.spinner("Salvataggio in corso..."):
                            try:

                                # Data preprocessing before insert in DB
                                # Copying data in case I'll use successful_results for visualization.
                                data_to_insert = [ r['data'] for r in successful_results]
                                for data in data_to_insert:
                                    # With postgres triggers, created_at and updated_at should be
                                    # automatically updated by the database.
                                    # data['data']['created_at'] = datetime.now().isoformat()
                                    # data['data']['updated_at'] = datetime.now().isoformat()
                                    data['user_id'] = st.session_state['user']['id']

                                result = supabase_client.table(table_name).insert(data_to_insert).execute()
                                print("Insert successful:", result.data)
                                st.success("Fatture salvate con successo nel database!")

                                # Clear session state after successful save
                                st.session_state.xml_processing_results = None
                                st.session_state.xml_processing_stage = 'saved'

                                time.sleep(2)
                                st.rerun()

                            except Exception as e:
                                st.error(f"❌ Errore durante il salvataggio: {str(e)}")
                                print(f"Save error: {str(e)}")
                                raise

                with col2:
                    if st.button("❌ Annulla", use_container_width=True):
                        st.rerun()
