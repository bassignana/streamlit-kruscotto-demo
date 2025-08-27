import streamlit as st
import pandas as pd
from utils import setup_page, create_monthly_line_chart, get_standard_column_config


def main():
    user_id, supabase_client, page_can_render = setup_page()

    if page_can_render:

        overview, emesse, ricevute = st.tabs(["Riepilogo", "Fatture Emesse", "Fatture Ricevute"])

        with overview:
            result = supabase_client.table('monthly_invoice_summary').select('*').execute()

            if not result.data:
                st.warning("Nessun dato disponibile per il periodo selezionato")

            # I need this else otherwise when I do df.columns[0] I get an Index error
            else:

                df = pd.DataFrame(result.data)

                df.columns = [
                    col.replace('_', ' ').title() # if isinstance(col, str) else str(col)
                    for col in df.columns
                ]

                index_column = 'Tipo Fattura'
                money_columns = df.columns.tolist().copy()
                money_columns.remove(index_column)

                column_config = get_standard_column_config(money_columns = money_columns)

                # NOTE that here I use an index just for visual reasons.
                df = df.set_index(index_column)

                st.dataframe(df, use_container_width=True, column_config = column_config)

                fig = create_monthly_line_chart(df,"Fatture di Vendita", "Fatture di Acquisto")
                st.plotly_chart(fig)

        with emesse:
            result = supabase_client.table('fatture_emesse_overview').select('*').execute()

            if not result.data:
                st.warning("Nessun dato disponibile per il periodo selezionato")
            else:
                df = pd.DataFrame(result.data)

                df.columns = [
                    col.replace('_', ' ').title() # if isinstance(col, str) else str(col)
                    for col in df.columns
                ]

                money_columns = ['Totale', 'Incassato', 'Saldo']
                date_columns = ['Data']
                column_config = get_standard_column_config(money_columns = money_columns,
                                                           date_columns = date_columns)

                st.dataframe(df, use_container_width=True, hide_index = True,
                             column_config = column_config)

        with ricevute:
            result = supabase_client.table('fatture_ricevute_overview').select('*').execute()

            if not result.data:
                st.warning("Nessun dato disponibile per il periodo selezionato")
            else:
                df = pd.DataFrame(result.data)

                df.columns = [
                    col.replace('_', ' ').title() if isinstance(col, str) else str(col)
                    for col in df.columns
                ]

                money_columns = ['Totale', 'Pagato', 'Saldo']
                date_columns = ['Data']
                column_config = get_standard_column_config(money_columns = money_columns,
                                                           date_columns = date_columns)

                st.dataframe(df, use_container_width=True, hide_index = True,
                             column_config = column_config)

if __name__ == "__main__":
    main()