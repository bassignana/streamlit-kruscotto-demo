import streamlit as st
import pandas as pd
from utils import setup_page
import plotly.graph_objects as go


def create_monthly_line_chart(df, sales_row_name="Fatture di Vendita", purchase_row_name="Fatture di Acquisto"):
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



def main():
    user_id, supabase_client, page_can_render = setup_page()

    if page_can_render:

        overview, emesse, ricevute = st.tabs(["Riepilogo", "Fatture Emesse", "Fatture Ricevute"])

        with overview:
            # TODO; .eq('user_id', user_id) AM I ENFORCING THIS?
            result = supabase_client.table('monthly_invoice_summary').select('*').execute()

            if not result.data:
                st.warning("Nessun dato disponibile per il periodo selezionato")
            else:
                # I need this else otherwise when I do df.columns[0] I get an Index error
                #TODO: value formatting
                df = pd.DataFrame(result.data)

                # Assumning that I force the first column of the view to be the index one.
                df = df.set_index(df.columns[0])
                # TODO; df.columns = ["Voce"] + df.columns[1:]

                df.columns = [
                    col.replace('_', ' ').title() if isinstance(col, str) else str(col)
                    for col in df.columns
                ]

                # TODO: scroll bar always preset, auto formatting everything to euro, remove some options.
                st.dataframe(df, use_container_width=True)

                fig = create_monthly_line_chart(df)
                st.plotly_chart(fig)

        with emesse:
            result = supabase_client.table('fatture_emesse_overview').select('*').execute()

            if not result.data:
                st.warning("Nessun dato disponibile per il periodo selezionato")
            else:
                df = pd.DataFrame(result.data)

                # TODO; title() here will cause problems.
                # Assumning that I force the first column of the view to be the index one.
                df = df.set_index(df.columns[0])
                df.columns = [
                    col.replace('_', ' ').title() if isinstance(col, str) else str(col)
                    for col in df.columns
                ]

                st.dataframe(df, use_container_width=True)


        with ricevute:
            result = supabase_client.table('fatture_ricevute_overview').select('*').execute()

            if not result.data:
                st.warning("Nessun dato disponibile per il periodo selezionato")
            else:
                df = pd.DataFrame(result.data)

                # TODO; title() here will cause problems.
                # Assumning that I force the first column of the view to be the index one.
                df = df.set_index(df.columns[0])
                df.columns = [
                    col.replace('_', ' ').title() if isinstance(col, str) else str(col)
                    for col in df.columns
                ]

                st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()