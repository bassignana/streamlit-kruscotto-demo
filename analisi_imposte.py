from decimal import Decimal, ROUND_HALF_UP
import plotly.graph_objects as go
import streamlit as st

from config import uppercase_prefixes
from utils import setup_page, get_df_metric, remove_prefix
import pandas as pd

from altri_movimenti_config import altri_movimenti_config
from altri_movimenti_utils import render_movimenti_crud_page

def main():
    user_id, supabase_client, page_can_render = setup_page("Gestione Altri Movimenti")
    imposta1, imposta2 = st.tabs(["Imposta 1", "Imposta 2"])

    if page_can_render:

        with imposta1:
            result = supabase_client.table('movimenti_passivi').select('*') \
                .eq('mp_tipo', 'IMPOSTA').execute()

            if not result.data:
                st.warning("Nessuna imposta presente nei movimenti passivi")
            else:

                soglia = st.number_input('Soglia imposta X', value = 50, disabled = True, width = 100)

                df = pd.DataFrame(result.data)
                df.columns = [
                    col.replace('_', ' ').title() if isinstance(col, str) else str(col)
                    for col in df.columns
                ]
                df.columns = [remove_prefix(col, uppercase_prefixes) for col in df.columns]

                importo_dovuto = df['Importo Totale'].sum()
                st.write(f'Totale dovuto: {importo_dovuto}')
                if importo_dovuto >= soglia*0.8 and importo_dovuto <= soglia:
                    st.warning("Soglia importo quasi raggiunta")
                elif importo_dovuto > soglia:
                    st.error("Soglia importo superata")
        with imposta2:
            st.write('todo')



if __name__ == '__main__':
    main()
