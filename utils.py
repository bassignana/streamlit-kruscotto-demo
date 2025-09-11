import streamlit as st
import plotly.graph_objects as go
from auth_utils import show_login_and_render_form, show_simple_login_form
import postgrest
import logging
from decimal import Decimal, ROUND_HALF_UP, getcontext
from datetime import datetime, date
import pandas as pd

def to_money(amount):
    getcontext().prec = 28
    MONEY_QUANTIZE    = Decimal('0.01')  # 2 decimal places
    CURRENCY_ROUNDING = ROUND_HALF_UP

    if amount is None:
        decimal_amount = Decimal(0)
    else:
        decimal_amount = Decimal(str(amount))
    return decimal_amount.quantize(MONEY_QUANTIZE, rounding=CURRENCY_ROUNDING)

def get_df_metric(label, amount):
    with st.container():
        df = pd.DataFrame({label: to_money(amount)},
                          index = [0])

        # df = df.style.set_properties(**{
        #     'font-size': '70pt',
        #     # 'font-weight': 'bold'
        # })

        # styler = df.style
        # styler.applymap_index(lambda v: "font-weight: bold;", axis="index")

        column_config = {}
        for col in df.columns:
            column_config[col] = st.column_config.NumberColumn(
                label=col,
                format="localized",
            )

        st.dataframe(df, hide_index = True, column_config=column_config)


# Ugly version.
# def get_df_metric(label, amount):
#     with st.container():
#         df = pd.DataFrame({label: to_money(amount)}, index=[0])
#
#         styled_df = df.style.set_table_styles([
#             {'selector': 'th', 'props': [('font-weight', 'bold'), ('font-size', '16px')]}
#         ])
#
#         st.markdown(styled_df.to_html(), unsafe_allow_html=True)

def fetch_all_records(supabase_client, table_name: str, user_id: str):
    try:
        result = supabase_client.table(table_name).select('*').eq('user_id', user_id).execute()

        if result.data:
            return result.data
        else:
            return []
    except Exception as e:
        logging.exception(f"Database error in fetch_all_records - error: {e} - table: {table_name}, user_id: {user_id}")
        raise

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
        show_login_and_render_form(supabase_client)
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
            st.warning("Prima di usare l'applicazione è necessario impostare l'anagrafica azienda")
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
                               date_columns = None,
                               required_columns = None):

    # required = True if col in required_columns else False
    #
    # Don't do this, it will mess with the process of validation before saving,
    # probably because the dataframe does not return an incomplete row, but it
    # is very unfriendly to the user.


    if required_columns is None:
        required_columns = []

    column_config = {}

    if money_columns is not None:
        for col in money_columns:
            column_config[col] = st.column_config.NumberColumn(
                label=col + '*' if col in required_columns else col,
                format="localized",
            )

    # todo: do I need to start with None param in the signature and check?
    if date_columns is not None:
        for col in date_columns:
            column_config[col] = st.column_config.DateColumn(
                label=col + '*' if col in required_columns else col,
                format="MM/DD/YYYY",
            )

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

def fetch_record_from_id(supabase_client, table_name, record_id, user_id = st.session_state.user.id):

    # todo: better error handling and check for one single row
    try:
        result = supabase_client.table(table_name).select('*') \
            .eq('user_id', user_id) \
            .eq('id', record_id).execute()

        if result.data:
            return result.data[0]
        else:
            return {}
    except Exception as e:
        logging.exception(f"Database error in fetch_all_records_from_view: {e}")
        raise

def money_to_string(amount):

    if not isinstance(amount, Decimal):
        amount = to_money(amount)

    return str(amount)

def render_field_widget(field_name, field_config, default_value = None, key_suffix = "", disabled = False, index = 0):
    """Render appropriate SINGLE input widget based on field configuration"""

    field_type = field_config.get('data_type', 'string')
    label = field_config.get('label', field_name.replace('_', ' ').title())
    widget_key = f"{field_name}_{key_suffix}" if key_suffix else field_name
    help_text = field_config.get('help')
    required = field_config.get('required', False)

    # Add asterisk for required fields
    if required:
        label += " *"

    if field_type == 'string':
        return st.text_input(
            label,
            value=default_value or "",
            key=widget_key,
            placeholder=field_config.get('placeholder'),
            help=help_text,
            disabled=disabled
        )
    elif field_type == 'selectbox':
        options = field_config.get('options', ['Missing options in config file'])
        return st.selectbox(
                label,
                index = index,
                options=options,
                key=widget_key,
                help=help_text,
                disabled=disabled
            )

    elif field_type == 'money':
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
            help=help_text,
            disabled=disabled
        )

    elif field_type == 'integer':
        return st.number_input(
            label,
            value=int(default_value) if default_value else 0,
            step=1,
            key=widget_key,
            help=help_text,
            disabled=disabled
        )

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
                help=help_text,
                disabled=disabled
            )
        else:
            return st.date_input(
                value = None,
                label = label,
                key=widget_key,
                help=help_text,
                disabled=disabled
            )

    # Boolean fields
    elif field_type == 'boolean':
        return st.checkbox(
            label,
            value=bool(default_value) if default_value is not None else False,
            key=widget_key,
            help=help_text,
            disabled=disabled
        )

    # Fallback to text input
    else:
        return st.text_input(
            label,
            value=str(default_value) if default_value else "",
            key=widget_key,
            help=help_text,
            disabled=disabled
        )

def are_all_required_fields_present(form_data, sql_table_fields_names, fields_config):
    errors = []
    for field_name, field_config in fields_config.items():
        if field_config.get('required', False) and field_name in sql_table_fields_names:
            value = form_data.get(field_name)
            if not value or (isinstance(value, str) and not value.strip()):
                prefix_len = len(field_name.split('_')[0]) + 1

                errors.append(f"Il campo '{field_name[prefix_len:].title()}' è obbligatorio.")
    return errors

def remove_prefix(col_name, prefixes):
    for prefix in prefixes:
        if col_name.startswith(prefix):
            return col_name[len(prefix):]
    return col_name  # Return original if no prefix found

def format_italian_currency(val):
    """Italian currency: 1.250,50

    Usage:
    df = df.style.format({
     'Importo Totale': format_italian_currency,
     })
    """
    if pd.isna(val):
        return "0,00"
    formatted = f"{val:,.2f}"
    formatted = formatted.replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')
    return f"{formatted}"
