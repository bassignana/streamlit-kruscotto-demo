import streamlit as st
import plotly.graph_objects as go

def setup_page(page_title = "", page_icon = ""):
    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout="wide"
    )

    if 'user' not in st.session_state or not st.session_state.user:
        st.error("🔐 Please login first")
        st.stop()
    user_id = st.session_state.user.id

    if 'client' not in st.session_state:
        st.error("Please create the client for invoice_uploader")
        st.stop()
    supabase_client = st.session_state.client

    response = supabase_client.table('user_data').select("*").eq('user_id',user_id).execute()

    # Flag for avoiding rendering the page content in case the anagrafica azienda is not set yet.
    page_can_render = True
    if len(response.data) < 1:
        page_can_render = False
        st.warning("Prima di usare l'applicazione e' necessario impostare l'anagrafica azienda")
        switched = st.button("Imposta Anagrafica Azienda", type='primary')
        if switched:
            st.switch_page("page_anagrafica_azienda.py")


    return user_id, supabase_client, page_can_render

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
