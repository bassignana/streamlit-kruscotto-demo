import streamlit as st
import pandas as pd
from utils import setup_page, fetch_all_records


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
                width = 78
            )
        else:
            column_config[col] = st.column_config.NumberColumn(
                label=col,
                format="localized",
                width = 95
            )

    return column_config

def are_terms_total_congruent(supabase_client, table_name, user_id, prefix):

    # Here I fetch data to be sure to have the most up to date data,
    # but in the future this might be simplified.
    check_documents = fetch_all_records(supabase_client, table_name, user_id)
    check_terms = pd.DataFrame(fetch_all_records(supabase_client, 'rate_' + table_name, user_id))
    errors = []

    if 'fatture' in table_name:
        for invoice in check_documents:

            number_key = invoice[prefix + 'numero_fattura']
            date_key = invoice[prefix + 'data_documento']

            i_terms = check_terms[(check_terms['r' + prefix + 'numero_fattura'] == number_key) & \
                                  (check_terms['r' + prefix + 'data_documento'] == date_key)]


            total_i = invoice[prefix + 'importo_totale_documento']
            total_i_terms = i_terms['r' + prefix + 'importo_pagamento_rata'].sum()

            if total_i != total_i_terms:
                errors.append((f'La fattura numero {number_key}, in data {date_key} ha un importo '
                           f'totale di {total_i} Euro, mentre le relative scadenze hanno un importo '
                           f'totale di {total_i_terms} Euro.'))

        return errors

    elif 'movimenti' in table_name:
        for movement in check_documents:

            number_key = movement[prefix + 'numero']
            date_key = movement[prefix + 'data']

            i_terms = check_terms[(check_terms['r' + prefix + 'numero'] == number_key) & \
                                  (check_terms['r' + prefix + 'data'] == date_key)]


            total_i = movement[prefix + 'importo_totale']
            total_i_terms = i_terms['r' + prefix + 'importo_pagamento'].sum()

            if total_i != total_i_terms:
                errors.append((f'Il movimento numero {number_key}, in data {date_key} ha un importo '
                               f'totale di {total_i} Euro, mentre le relative scadenze hanno un importo '
                               f'totale di {total_i_terms} Euro.'))

        return errors

    else:
        raise Exception("Check terms congruency: table name not supported")


def main():
    user_id, supabase_client, page_can_render = setup_page("Gestione Altri Movimenti")

    active_errors = are_terms_total_congruent(supabase_client, 'fatture_emesse', user_id, 'fe_')
    passive_errors = are_terms_total_congruent(supabase_client, 'fatture_ricevute', user_id, 'fr_')
    discrepancy_errors = active_errors + passive_errors
    if any(discrepancy_errors):
        with st.expander('Errori Gravi', expanded = True):
            st.error('Le cifre in questa pagina saranno errate fino a quando gli errori qui sotto non verranno corretti.')
            for e in discrepancy_errors:
                st.warning(e)

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
                'Netto 30gg',
                'Netto 60gg',
                'Netto 90gg',
                'Totale'
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
