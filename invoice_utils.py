import time

import streamlit as st
import pandas as pd
from datetime import datetime, date
from decimal import Decimal, getcontext
from invoice_xml_processor import process_xml_list
from invoice_record_creation import extract_xml_records
from utils import extract_field_names, render_field_widget


# def render_add_form(supabase_client, table_name, fields_config, prefix):
#
#     with st.form(f"add_{table_name}_form",
#                  clear_on_submit=True,
#                  enter_to_submit=False):
#
#         form_data = {}
#         field_items = list(fields_config.items())
#
#         sql_table_fields_names = extract_field_names('sql/02_create_tables.sql', prefix)
#
#         cols = st.columns(2)
#         for i, (field_name, field_config) in enumerate(field_items):
#             with cols[i % 2]:
#                 if field_name in sql_table_fields_names:
#                     form_data[field_name] = render_field_widget(
#                         field_name, field_config, key_suffix=f"add_{table_name}"
#                     )
#
#         col1, col2 = st.columns([1, 1])
#
#         with col1:
#             submitted = st.form_submit_button("Salva", type="primary")
#
#         with col2:
#             cancelled = st.form_submit_button("Annulla")
#
#         if cancelled:
#             st.rerun()
#
#         if submitted:
#             try:
#                 is_valid, errors = validate_required_form_data(fields_config, form_data)
#
#                 if not is_valid:
#                     for error in errors:
#                         st.error(error)
#                 else:
#                     processed_data = {}
#                     # todo: the correct thing should be creating
#                     # default values for all non required fields,
#                     # that is consistent throughout all fields and
#                     # compatible with a direct upload to the database.
#                     # Maybe a string, for sure not None.
#                     #
#                     # For now I'm just uploading the str() version of whatever
#                     # value I get from form_data and dropping non required fields
#                     for field_name, field_config in fields_config.items():
#                         if field_config.get('required', False):
#                             value = form_data.get(field_name)
#                             # for field_name, value in form_data.items():
#                             processed_data[field_name] = str(value)
#
#
#                     prefixed_processed_data = {}
#                     for k,v in processed_data.items():
#                         prefixed_processed_data[prefix + k] = v
#                     prefixed_processed_data['user_id'] = st.session_state.user.id
#
#
#                     # Correct format to use for save_to_database()
#                     # todo: now that I don't use save_to_database() anymore
#                     # do I have to keep this format?
#                     data_to_upload = {}
#                     data_to_upload['data'] = prefixed_processed_data
#                     data_to_upload['status'] = 'success'
#                     list_data = []
#                     list_data.append(data_to_upload)
#                     print(list_data)
#
#                     with st.spinner("Salvataggio in corso..."):
#                         successful_results = [r.get('data') for r in list_data if r['status'] == 'success']
#
#                         try:
#                             result = supabase_client.table(table_name).insert(successful_results).execute()
#                             st.success("Fattura salvata con successo nel database!")
#                             # todo: for resetting fields on reload I have to delete these
#                             # keys in the session state, or understand where they are formed
#                             # and clean them up some other way.
#                             # "numero_fattura_add_fatture_emesse":"1"
#                             # "partita_iva_prestatore_add_fatture_emesse":"1"
#                             # "data_scadenza_pagamento_add_fatture_emesse":NULL
#                             # "data_documento_add_fatture_emesse":"datetime.date(2025, 7, 31)"
#                             st.rerun()
#                         except Exception as e:
#                             st.error("Error inserting data:", e)
#
#             except Exception as e:
#                 print(f'Error adding invoice manually: {e}')

def to_decimal(value) -> Decimal:
    """Convert value to Decimal with proper precision"""
    if value is None or value == '':
        return Decimal('0.00')
    try:
        clean_value = str(value).strip().replace(',', '.')
        return Decimal(clean_value)
    except Exception as e:
        raise Exception('Invalid Decimal conversion') from e


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
        # if field_type == 'money' and value is not None:
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
            #         elif field_type == 'money' and not df[col].isna().all():
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
            #     if field_type == 'money' and value is not None:
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
            process_button = st.button("🔄 Elabora Fatture", type="primary")

        with col2:
            if st.button("❌ Cancella"):
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
                #         if field_type == 'money':
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
                    if st.button("✅ Conferma e Salva nel Database", type="primary"):
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
                                    data['user_id'] = st.session_state.user.id

                                result = supabase_client.table(table_name).insert(data_to_insert).execute()
                                print("Insert successful:", result.data)
                                st.success("Fatture salvate con successo nel database!")

                                # Clear session state after successful save
                                st.session_state.xml_processing_results = None
                                st.session_state.xml_processing_stage = 'saved'

                                time.sleep(1)
                                st.rerun()

                            except Exception as e:
                                st.error(f"Errore durante il salvataggio: {str(e)}")
                                print(f"Save error: {str(e)}")
                                raise

                with col2:
                    if st.button("❌ Annulla"):
                        st.rerun()

def render_modify_form(supabase_client, user_id, table_name, fields_config, data_df, record_id, prefix):
    # TODO; can I use unprefixed fields everywhere in all these functions?

    # TODO
    # if data_df.empty or record_id not in data_df['id'].values:
    #     st.error("Nessuna fattura trovata")
    #     return

    # Ensure snake_case for column names, otherwise problems with standard naming in the
    # following operations.
    data_df.columns = [
        col.replace(' ', '_' ).lower() if isinstance(col, str) else str(col)
        for col in data_df.columns
    ]

    record = data_df[data_df['id'] == record_id]

    # I want to show in the modify form only the field relevant to the invoice, and not
    # the tech fileds like id, created at etc.
    # In order to do that I select only the column that starts with the prefix.
    cols = [c for c in data_df.columns if c.startswith(prefix)]
    record = record[cols]

    # Ensure column names are not prefixed, otherwise getting the value from each column will fail.
    record.columns = [
        col[(len(prefix)):] if col.startswith(prefix) else col
        for col in record.columns
    ]

    # For some reason, the below will create nested dicts, where each value is a dict with one element.
    # record = record.to_dict()

    record_data = {}
    for col in record.columns:
        record_data[col] = record[col].iloc[0]

    with st.form(f"modify_{table_name}_form"):
        # form_data will hold the updated value of the form when I click on the
        # Aggiorna button. This is because, for some reason, the code below will rerun
        # and update form_data.
        form_data = {}

        field_items = list(fields_config.items())

        sql_table_fields_names = extract_field_names('sql/02_create_tables.sql', prefix)

        cols = st.columns(2)
        for i, (field_name, field_config) in enumerate(field_items):
            with cols[i % 2]:
                if field_name in sql_table_fields_names:
                    # TODO; how do I manage the case where the record has not a value?
                    #  I can try with None, but I have to test this more thoroughly.
                    record_value = record_data.get(field_name, None)

                    #TODO; another problem here is the data format, that has to be enforced.
                    # somehow, for example, one PIVA is in string the other is a float.
                    form_data[field_name] = render_field_widget(
                        field_name, field_config, record_value,
                        key_suffix=f"modify_{table_name}"
                    )

        col1, col2 = st.columns([1, 1])

        with col1:
            submitted = st.form_submit_button("💾 Aggiorna", type="primary")

        with col2:
            cancelled = st.form_submit_button("🚫 Annulla")

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
                    processed_data['user_id'] = st.session_state.user.id

                    # From the code above, we know that form_data will hold either a value or None,
                    # and we know that if we pass None, the supabase API will convert to NONE or
                    # default value.
                    for name, value in form_data.items():
                        # All string otherwise 'Object of type date is not JSON serializable'
                        processed_data[prefix + name] = str(value)

                    with st.spinner("Salvataggio in corso..."):
                        result = supabase_client.table(table_name).update(processed_data).eq('id', record_id).execute()
                        if result:
                            st.success("Fattura salvata con successo nel database!")
                            time.sleep(1)
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
        #         if field_type == 'money':
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

def render_delete_confirmation(supabase_client, user_id, table_name, fields_config, data_df, record_ids:list[str]):
    #
    # if data_df.empty or record_id not in data_df['id'].values:
    #     st.error("Record non trovato")
    #     return

    st.warning(f"Selezionate {len(record_ids)} fatture. Sei sicuro di voler eliminare questa fattura? L'operazione non può essere annullata.")

    # # Show record details
    # with st.expander("Visualizza dettagli fattura"):
    #     for id in record_ids:
    #
    #         field_label = get_field_label(fields_config, field_name)
    #         field_value = record.get(field_name, "")
    #
    #         # Format value based on type
    #         field_type = fields_config.get(field_name, {}).get('data_type', 'string')
    #         if field_type == 'money' and field_value:
    #             field_value = f"€ {float(field_value):,.2f}"
    #         elif field_type == 'date' and field_value:
    #             if isinstance(field_value, (date, datetime)):
    #                 field_value = field_value.strftime('%d/%m/%Y')
    #         elif field_type == 'boolean':
    #             field_value = "Sì" if field_value else "No"
    #
    #         st.write(f"**{field_label}:** {field_value}")

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Conferma Eliminazione", type="primary"):
            try:

                with st.spinner("Salvataggio in corso..."):
                    # todo: check this.
                    # Supabase delete always returns empty data, so we check for no exception
                    for id in record_ids:
                        result = supabase_client.table(table_name).delete().eq('id', id).execute()
                        if result:
                            pass
                    st.success("Fatture eliminate con successo")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                print(f'Error deleting fattura: {e}')
                raise

    with col2:
        if st.button("🚫 Annulla"):
            st.session_state[f"crud_mode_{table_name}"] = "view"
            st.rerun()

def get_field_label(fields_config, field_name):
    """Get display label for field"""
    config = fields_config.get(field_name, {})
    return config.get('label', field_name.replace('_', ' ').title())

# For now I'll not use this. Implement later if needed.
def xml_to_db_cleaning(parsed_xml_data: dict[str,str], field_mappings) -> (dict, str):
    """
    # todo: maybe this function is only used in one case, from xml to db op. Because
    # its input is the data dictionary in the parsed xml datat structure.
    NOTE: python types are good for both insert statements, where data is sent to the database
          and for python operations.

    parsed_xml_data: data field OF ONE INVOICE of the output data structure of invoice_xml_preprocessor.py.
                     Here I expect the key to be the sql column name without prefix,
                     and the value to be the value to cast.
    return: copy of original data with correct types.
            data, null if no error
            null, str(error) if error
    """
    getcontext().prec = 2 # This should affect global decimal context
    result = {}

    try:
        #todo: who should have the responsibility to check that a required field is present or not?

        # Looping over data and not over config because, if somewhere else I check that all required fields
        # are present, here I don't have to do again the check for KeyError i.e. missing field in data but
        # present in config.
        for (field_name, value) in parsed_xml_data.items():
            match field_mappings[field_name]['data_type']:

                case 'string':
                    result[field_name] = str(value).strip()

                case 'int':
                    # For now there is no int, but be careful to use int as
                    # it will mismanage trailing 0s
                    result[field_name] = int(value.strip())

                case 'money':
                    clean_decimal = str(value).strip().replace(',', '.')

                    # To string because 'Object of type Decimal is not JSON serializable'
                    result[field_name] = str(Decimal(clean_decimal))

                case 'date':
                    # From the docs I know that the date is in ISO 8610 format.
                    is_list = isinstance(value, list)
                    is_string = isinstance(value, str)

                    if not is_list and not is_string :
                        raise Exception('Input date value from XML is not a list or string.')

                    if is_string:
                        # Don't convert to date, otherwise
                        # 'Object of type datetime is not JSON serializable'
                        # result[field_name] = datetime.fromisoformat(value)
                        result[field_name] = value.strip()
                    else:
                        result[field_name] = [ d.strip() for d in value ]

                case _:
                    raise Exception('Uncaught error in match statement, xml_to_db_cleaning')

    except Exception as e:
        return None, str(e)

    return result, None

def render_selectable_dataframe(query_result_data, selection_mode = 'single_row', on_select = 'rerun'):
    df = pd.DataFrame(query_result_data)

    df.columns = [
        col.replace('_', ' ').title() if isinstance(col, str) else str(col)
        for col in df.columns
    ]

    df = df.drop(['Id', 'User Id', 'Created At', 'Updated At'], axis = 1)

    uppercase_prefixes = ['Fe ', 'Fr ', 'Rfe ', 'Rfr ', 'Ma ', 'Mp ', 'Rma ', 'Rmp ']
    def remove_prefix(col_name, prefixes):
        for prefix in prefixes:
            if col_name.startswith(prefix):
                return col_name[len(prefix):]
        return col_name  # Return original if no prefix found

    df.columns = [remove_prefix(col, uppercase_prefixes) for col in df.columns]

    selection = st.dataframe(df, use_container_width=True,
                             selection_mode = selection_mode,
                             on_select=on_select,
                             hide_index = True)

    return selection