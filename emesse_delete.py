import streamlit as st

from invoice_utils import render_data_table, render_delete_confirmation
from xml_mapping_emesse import XML_FIELD_MAPPING as fields_config

# def render_data_table(supabase_client, user_id, table_name, fields_config, display_name = None, search_enabled = True):
#     """Render data table with optional search and return selected record ID"""
#     display_name = display_name or table_name.replace('_', ' ').title()
#     st.subheader(f"Elimina {display_name}")
#     st.write("Fatture Emesse disponibili:")
#
#     # Load data from database
#     data_df = fetch_all_records(supabase_client, table_name, user_id)
#
#     if data_df.empty:
#         st.info(f"Nessun record trovato per {display_name}")
#         return None
#
#     # Search functionality
#     if search_enabled:
#         search_term = st.text_input("🔍 Cerca", placeholder="Digita per cercare...")
#
#         if search_term:
#             # Search in all string columns
#             string_cols = [col for col in data_df.columns
#                            if data_df[col].dtype == 'object' and col not in ['id']]
#
#             if string_cols:
#                 mask = data_df[string_cols].astype(str).apply(
#                     lambda x: x.str.contains(search_term, case=False, na=False)
#                 ).any(axis=1)
#                 data_df = data_df[mask]
#
#     # Display table
#     if not data_df.empty:
#         # Prepare display dataframe (hide system columns)
#         display_df = data_df.copy()
#         system_cols = ['id', 'created_at', 'updated_at', 'user_id']
#         display_df = display_df.drop(columns=[col for col in system_cols if col in display_df.columns])
#
#         # Format columns based on field types
#         # for col in display_df.columns:
#         #     if col in fields_config:
#         #         field_type = get_field_type(fields_config, col)
#         #         if field_type == 'money':
#         #             display_df[col] = display_df[col].apply(
#         #                 lambda x: f"€ {float(x):,.2f}" if pd.notna(x) else ""
#         #             )
#         #         elif field_type == 'date':
#         #             display_df[col] = pd.to_datetime(display_df[col]).dt.strftime('%d/%m/%Y')
#         #         elif field_type == 'boolean':
#         #             display_df[col] = display_df[col].apply(lambda x: "Sì" if x else "No")
#
#         # Rename columns for display
#         # display_columns = {}
#         # for col in display_df.columns:
#         #     if col in fields_config:
#         #         display_columns[col] = get_field_label(fields_config, col)
#         # display_df = display_df.rename(columns=display_columns)
#
#         # Show table
#         st.dataframe(display_df, use_container_width=True)
#
#         # Row selection using selectbox
#         if len(data_df) > 0:
#
#             # Create options for selectbox
#             options = ["Nessuna selezione"]
#             record_map = {}
#
#             for idx, row in data_df.iterrows():
#                 # Create a readable identifier
#                 identifier_fields = ['numero_fattura', 'name', 'numero', 'cliente']
#                 identifier = None
#
#                 for field in identifier_fields:
#                     if field in row and pd.notna(row[field]):
#                         identifier = str(row[field])
#                         break
#
#                 if not identifier:
#                     # Fallback to first non-system field
#                     for col in row.index:
#                         if col not in system_cols and pd.notna(row[col]):
#                             identifier = str(row[col])
#                             break
#
#                 if not identifier:
#                     identifier = f"Record {idx}"
#
#                 display_text = f"{identifier} (ID: {row['id'][:8]}...)"
#                 options.append(display_text)
#                 record_map[display_text] = row['id']
#
#             selected_option = st.selectbox(
#                 "Clicca o digita per selezionare una fattura:",
#                 options=options,
#                 key=f"select_record_{table_name}"
#             )
#
#             if selected_option != "Nessuna selezione":
#                 return record_map[selected_option]
#
#     return None


def main():

    st.set_page_config(
        page_title="Rimuovi Fattura Emessa",
        page_icon="📄",
        layout="wide"
    )

    if 'user' not in st.session_state or not st.session_state.user:
        st.error("🔐 Please login first")
        st.stop()
    user_id = st.session_state.user.id

    if 'client' not in st.session_state:
        st.error("Please create the client for pate_test_uploader")
        st.stop()
    supabase_client = st.session_state.client

    st.subheader('Elimina Fattura Emessa')

    selected_id = render_data_table(supabase_client, user_id, 'fatture_emesse', fields_config, 'Fattura emessa', search_enabled=False)
    if selected_id:
        st.write("---")
        render_delete_confirmation(supabase_client, user_id, 'fatture_emesse', fields_config, selected_id, 'Fattura emessa')
    else:
        # st.info("👆 Seleziona un record dalla tabella per eliminarlo")
        pass


if __name__ == "__main__":
    main()