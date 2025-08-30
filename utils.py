import streamlit as st
import plotly.graph_objects as go
from auth_utils import show_login_form, show_simple_login_form
import postgrest
import logging



def setup_page(page_title = "", page_icon = "", enable_page_can_render_warning = True):
    """
    enable_page_can_render_warning is False only for the page that shows the anagrafica form,
    otherwise the warning will always be present on the top of the anagrafica form's page.
    """

    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout="wide"
    )
    if 'client' not in st.session_state:
        st.error("Please create the client for invoice_uploader")
        st.stop()
    supabase_client = st.session_state.client

    if 'user' not in st.session_state or not st.session_state.user:
        # st.error("🔐 Please login first")
        # st.stop()
        show_login_form(supabase_client)
    user_id = st.session_state.user.id

    # Todo: if in the page there are tabs, the tabs will be shown even if the
    #  login form is displayed and I return false for the page can render variable.
    try:
        response = supabase_client.table('user_data').select("*").eq('user_id',user_id).execute()
    except postgrest.exceptions.APIError as e:
        if 'JWT expired' in e.message:
            st.info('Sessione scaduta, effettuare il login nuovamente')
            # TODO: test this simple form
            show_simple_login_form(supabase_client)
            return user_id, supabase_client, False


    if enable_page_can_render_warning:
        # Flag for avoiding rendering the page content in case the anagrafica azienda is not set yet.
        page_can_render = True
        if len(response.data) < 1:
            page_can_render = False
            st.warning("Prima di usare l'applicazione e' necessario impostare l'anagrafica azienda")
            switched = st.button("Imposta Anagrafica Azienda", type='primary')
            if switched:
                st.switch_page("page_anagrafica_azienda.py")
        return user_id, supabase_client, page_can_render

    else:
        return user_id, supabase_client

def extract_field_names(sql_file_path ='sql/02_create_tables.sql', prefix='fe_'):
    field_names = []
    with open(sql_file_path, 'r') as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith(prefix):
                # Get first word (field name)
                field_name = stripped.split()[0]
                # Remove prefix because I have to check against field names in
                # the xml_fields which has names without prefix.
                field_name = field_name[len(prefix):]
                field_names.append(field_name)
    return field_names

def extract_prefixed_field_names(sql_file_path = 'sql/02_create_tables.sql', prefix='fe_'):
    field_names = []
    with open(sql_file_path, 'r') as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith(prefix):
                # Get first word (field name)
                field_name = stripped.split()[0]
                field_names.append(field_name)
    return field_names

def create_monthly_line_chart(df, sales_row_name, purchase_row_name):
    """
    Create a simple line chart from a DataFrame with monthly data.

    Args:
        df: DataFrame with months as columns and invoice types as index
        sales_row_name: Name of the sales row in the DataFrame index
        purchase_row_name: Name of the purchase row in the DataFrame index

    Returns:
        plotly Figure object
    """

    # Get x-axis (column names)
    months = df.columns.tolist()

    # Create figure
    fig = go.Figure()

    # Green line for sales
    if sales_row_name in df.index:
        sales_values = df.loc[sales_row_name].tolist()
        fig.add_trace(go.Scatter(
            x=months,
            y=sales_values,
            mode='lines+markers',
            name=sales_row_name,
            line=dict(color='green', width=3),
            marker=dict(size=8)
        ))

    # Red line for purchases
    if purchase_row_name in df.index:
        purchase_values = df.loc[purchase_row_name].tolist()
        fig.add_trace(go.Scatter(
            x=months,
            y=purchase_values,
            mode='lines+markers',
            name=purchase_row_name,
            line=dict(color='red', width=3),
            marker=dict(size=8)
        ))

    # Basic layout
    fig.update_layout(
        xaxis_title="Mesi",
        yaxis_title="Importo (€)",
        legend=dict(orientation="h", y=1.02),
        height=400
    )

    return fig

def get_standard_column_config(money_columns = None,
                               date_columns = None):

    column_config = {}

    if money_columns is not None:
        for col in money_columns:
            column_config[col] = st.column_config.NumberColumn(
                label=col,
                format="localized",
            )

    if date_columns is not None:
        for col in date_columns:
            column_config[col] = st.column_config.DateColumn(
                label=col,
                format="MM/DD/YYYY")

    return column_config

def fetch_all_records_from_view(supabase_client, view_name: str):
    try:
        result = supabase_client.table(view_name).select('*').execute()

        if result.data:
            return result.data
        else:
            return []
    except Exception as e:
        logging.exception(f"Database error in fetch_all_records_from_view: {e}")
        raise