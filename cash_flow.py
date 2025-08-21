import streamlit as st
import pandas as pd
from utils import setup_page

def main():
    user_id, supabase_client, page_can_render = setup_page("Gestione Altri Movimenti")

    active_result = supabase_client.table('active_cashflow_next_12_months_groupby_casse').select('*').execute()
    passive_result = supabase_client.table('passive_cashflow_next_12_months_groupby_casse').select('*').execute()

    if not active_result.data:
        st.warning("Nessun dato disponibile per i movimenti attivi")
    else:
        # I need this else otherwise when I do df.columns[0] I get an Index error
        #TODO: value formatting
        df = pd.DataFrame(active_result.data)

        # Assumning that I force the first column of the view to be the index one.
        active_df = df.set_index(df.columns[0])
        # TODO; df.columns = ["Voce"] + df.columns[1:]

        active_df.columns = [
            col.replace('_', ' ').title() if isinstance(col, str) else str(col)
            for col in active_df.columns
        ]

        # TODO: scroll bar always preset, auto formatting everything to euro, remove some options.
        st.subheader("Attivi")
        st.dataframe(active_df, use_container_width=True)

    if not passive_result.data:
        st.warning("Nessun dato disponibile per i movimenti passivi")
    else:
        df = pd.DataFrame(passive_result.data)
        passive_df = df.set_index(df.columns[0])

        passive_df.columns = [
            col.replace('_', ' ').title() if isinstance(col, str) else str(col)
            for col in passive_df.columns
        ]

        st.subheader("Passivi")
        st.dataframe(passive_df, use_container_width=True)

    if active_df is not None and passive_df is not None:
        try:
            # Get the last row from both dataframes (should be "Totali")
            active_totals = active_df.iloc[[-1]].copy()  # Last row as dataframe
            passive_totals = passive_df.iloc[[-1]].copy()  # Last row as dataframe

            saldo_columns = [
                'Saldo 30gg',
                'Saldo 60gg',
                'Saldo 90gg',
                'Saldo 120gg',
                'Saldo 150gg',
                'Saldo 180gg',
                'Saldo Oltre',
                'Saldo Scaduti 30gg',
                'Saldo Scaduti 60gg',
                'Saldo Scaduti 90gg',
                'Saldo Scaduti Oltre',
                'Saldo Netto',
                'Saldo Scaduti',
                'Saldo Totale'
            ]

            saldo = pd.DataFrame(active_totals.values - passive_totals.values,
                                 columns = saldo_columns)
            st.subheader('Totale')
            st.dataframe(saldo, use_container_width=True, hide_index=True)

            # # Convert all columns to numeric, filling NaN with 0
            # for col in active_totals.columns:
            #     active_totals[col] = pd.to_numeric(active_totals[col], errors='coerce').fillna(0)
            #
            # for col in passive_totals.columns:
            #     passive_totals[col] = pd.to_numeric(passive_totals[col], errors='coerce').fillna(0)
            #
            # # Align dataframes by columns (ensures same column structure)
            # active_totals, passive_totals = active_totals.align(passive_totals, fill_value=0)
            #
            # # Calculate net cashflow (active - passive)
            # net_df = active_totals - passive_totals
            # net_df.index = ['Netto']
            #
            # st.subheader("💰 Riepilogo Netto Totale")
            # st.dataframe(net_df, use_container_width=True)

        except Exception as e:
            st.error(f"Errore nel calcolo del netto: {str(e)}")
    else:
        st.warning("Per visualizzare il riepilogo netto sono necessari sia i dati attivi che passivi")

if __name__ == '__main__':
    main()
