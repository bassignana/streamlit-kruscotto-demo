import streamlit as st
import pandas as pd
from utils import setup_page

def get_cashflow_column_config(df_columns):
    column_config = {}
    months = [
        'Set',
        'Ott',
        'Nov',
        'Dic',
        'Gen',
        'Feb',
        'Mar',
        'Apr',
        'Mag',
        'Giu',
        'Lug',
        'Ago'
    ]
    for col in df_columns:
        if col == 'Cassa':
            column_config['Cassa'] = st.column_config.TextColumn(
                label='Cassa',
                width = 200
            )
        elif col[:3] in months:
            column_config[col] = st.column_config.NumberColumn(
                label=col[:3],
                format="localized",
                width = 60
            )
        else:
            column_config[col] = st.column_config.NumberColumn(
                label=col,
                format="localized",
                width = 100
            )

    return column_config

def main():
    user_id, supabase_client, page_can_render = setup_page("Gestione Altri Movimenti")

    active_result = supabase_client.table('active_cashflow_next_12_months_groupby_casse').select('*').execute()
    passive_result = supabase_client.table('passive_cashflow_next_12_months_groupby_casse').select('*').execute()

    if not active_result.data:
        st.warning("Nessun dato disponibile per i movimenti attivi")
    else:
        active_df = pd.DataFrame(active_result.data)
        active_df.columns = [
            col.replace('_', ' ').title() if isinstance(col, str) else str(col)
            for col in active_df.columns
        ]

        active_df = active_df.style.set_properties(
            subset=pd.IndexSlice[active_df.index[-1], :],
            **{'background-color': '#F6F7FA'}
        ).set_properties(
            subset=pd.IndexSlice[:, 'Cassa'],
            **{'color': '#75777E'}
        )

        column_config = get_cashflow_column_config(active_df.columns)

        st.subheader("Attivi")
        st.dataframe(active_df, use_container_width=True, column_config=column_config, hide_index = True)

    if not passive_result.data:
        st.warning("Nessun dato disponibile per i movimenti passivi")
    else:
        passive_df = pd.DataFrame(passive_result.data)
        passive_df.columns = [
            col.replace('_', ' ').title() if isinstance(col, str) else str(col)
            for col in passive_df.columns
        ]

        passive_df = passive_df.style.set_properties(
            subset=pd.IndexSlice[passive_df.index[-1], :],
            **{'background-color': '#F6F7FA'}
        ).set_properties(
            subset=pd.IndexSlice[:, 'Cassa'],
            **{'color': '#75777E'}
        )
        column_config = get_cashflow_column_config(passive_df.columns)

        st.subheader("Passivi")
        st.dataframe(passive_df, use_container_width=True, column_config=column_config, hide_index = True)


    # Since the formatting comes with the Styler object and I cannot use the dataframe without it,
    # I'm recreating the dataframes.
    active_df = pd.DataFrame(active_df.data)
    passive_df = pd.DataFrame(passive_df.data)
    if active_df is not None and passive_df is not None:
        try:
            active_totals = active_df.iloc[[-1]].copy()    # Last row as dataframe
            passive_totals = passive_df.iloc[[-1]].copy()  # Last row as dataframe

            active_totals = active_totals.drop('Cassa', axis=1)
            passive_totals = passive_totals.drop('Cassa', axis=1)

            saldo_columns = [
                'Set',
                'Ott',
                'Nov',
                'Dic',
                'Gen',
                'Feb',
                'Mar',
                'Apr',
                'Mag',
                'Giu',
                'Lug',
                'Ago',
                'Netto Oltre',
                'Scaduti 30gg',
                'Scaduti 60gg',
                'Scaduti 90gg',
                'Netto Scaduti'
            ]

            saldo = pd.DataFrame(active_totals.values - passive_totals.values,
                                 columns = saldo_columns)
            saldo.insert(0, "Cassa", 'Tutte le Casse')

            saldo = saldo.style.set_properties(
                subset=pd.IndexSlice[:, 'Cassa'],
                **{'color': '#75777E'}
            )

            column_config = get_cashflow_column_config(saldo.columns)

            st.subheader('Totale')
            st.dataframe(saldo, use_container_width=True, hide_index=True,  column_config=column_config)

        except Exception as e:
            st.error(f"Errore nel calcolo del netto: {str(e)}")
    else:
        st.warning("Per visualizzare il riepilogo netto sono necessari sia i dati attivi che passivi")

if __name__ == '__main__':
    main()
