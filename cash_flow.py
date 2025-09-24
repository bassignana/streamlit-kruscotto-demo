import traceback

import streamlit as st
import pandas as pd
from utils import setup_page, fetch_all_records, to_money

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

def get_cashflow_column_config(df_columns, months):
    column_config = {}

    for col in df_columns:
        if col == 'Cassa':
            column_config[col] = st.column_config.TextColumn(
                label='Cassa',
                width = 200,
                pinned = True
            )
        # Notice that there is no space in 'Oltre'. It is important to identify the column of saldo df.
        elif col == 'Incassare Oltre' or col == 'Pagare Oltre' or col == 'Oltre':
            column_config[col] = st.column_config.NumberColumn(
                label='Oltre',
                format="accounting",
                width = 78
            )
        # Notice that there is no space in 'Totale'. It is important to identify the column of saldo df.
        elif col == 'Totale Da Incassare' or col == 'Totale Da Pagare' or col == 'Totale':
            column_config[col] = st.column_config.NumberColumn(
                label='Totale',
                format="accounting",
                width = 78
            )
        elif col == 'Scaduti Oltre':
            column_config[col] = st.column_config.NumberColumn(
                label='Oltre',
                format="accounting",
                width = 78
            )
        elif col == 'Totale Scaduti':
            column_config[col] = st.column_config.NumberColumn(
                label='Totale',
                format="accounting",
                width = 78
            )
        elif col == 'Totale Attivi':
            column_config[col] = st.column_config.NumberColumn(
                label='Attività',
                format="accounting",
                width = 78
            )
        elif col == 'Totale Passivi':
            column_config[col] = st.column_config.NumberColumn(
                label='Passività',
                format="accounting",
                width = 78
            )

        elif 'gg' in col.lower() and 'scaduti' in col.lower():
            column_config[col] = st.column_config.NumberColumn(
                label=col.lower().replace('scaduti','').strip().upper(),
                format="accounting",
                width = 78
            )

        elif col[:3] in months:
            column_config[col] = st.column_config.NumberColumn(
                label=col[:3],
                format="accounting",
                width = 78
            )
        else:
            column_config[col] = st.column_config.NumberColumn(
                label=col,
                format="accounting",
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


            total_i = to_money(invoice[prefix + 'importo_totale_documento'])
            total_i_terms = to_money(i_terms['r' + prefix + 'importo_pagamento_rata'].sum())

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

    active_result = supabase_client.table('active_cashflow_next_12_months_groupby_casse').select('*').execute()
    passive_result = supabase_client.table('passive_cashflow_next_12_months_groupby_casse').select('*').execute()

    if not active_result.data:
        st.warning("Nessun dato disponibile per i movimenti attivi")
    else:
        active_df = pd.DataFrame(active_result.data).fillna(0.00)
        active_df.columns = [
            col.replace('_', ' ').title() if isinstance(col, str) else str(col)
            for col in active_df.columns
        ]

        # TODO; this is causing an error when I use multiIndex!
        #  Also for passivi.
        # active_df = active_df.style.set_properties(
        #     subset=pd.IndexSlice[active_df.index[-1], :],
        #     **{'background-color': '#F6F7FA'}
        # ).set_properties(
        #     subset=pd.IndexSlice[:, 'Cassa'],
        #     **{'color': '#75777E'}
        # )

        column_config = get_cashflow_column_config(active_df.columns, months)

        active_df.columns = pd.MultiIndex.from_arrays([[
               'ATTIVI',                    #cassa
               'Da Incassare',              #settembre
               'Da Incassare',              #ottobre
               'Da Incassare',              #novembre
               'Da Incassare',              #dicembre
               'Da Incassare',              #gennaio
               'Da Incassare',              #febbraio
               'Da Incassare',              #marzo
               'Da Incassare',              #aprile
               'Da Incassare',              #maggio
               'Da Incassare',              #giugno
               'Da Incassare',              #luglio
               'Da Incassare',              #agosto
               'Da Incassare',              #incassare_oltre
               'Da Incassare',              #totale_da_incassare
               'Da Incassare Scaduti',      #scaduti_30gg
               'Da Incassare Scaduti',      #scaduti_60gg
               'Da Incassare Scaduti',      #scaduti_oltre
               'Da Incassare Scaduti',      #totale_scaduti
               'Totale'                     #totale_attivi
                                                       ],
                active_df.columns])

        st.markdown("##### ATTIVI")
        st.dataframe(active_df, use_container_width=True, column_config=column_config, hide_index = True)

    if not passive_result.data:
        st.warning("Nessun dato disponibile per i movimenti passivi")
    else:
        passive_df = pd.DataFrame(passive_result.data).fillna(0.00)
        passive_df.columns = [
            col.replace('_', ' ').title() if isinstance(col, str) else str(col)
            for col in passive_df.columns
        ]

        # passive_df = passive_df.style.set_properties(
        #     subset=pd.IndexSlice[passive_df.index[-1], :],
        #     **{'background-color': '#F6F7FA'}
        # ).set_properties(
        #     subset=pd.IndexSlice[:, 'Cassa'],
        #     **{'color': '#75777E'}
        # )
        column_config = get_cashflow_column_config(passive_df.columns, months)

        passive_df.columns = pd.MultiIndex.from_arrays([[
            'PASSIVI',                   #cassa
            'Da Pagare',                 #settembre
            'Da Pagare',                 #ottobre
            'Da Pagare',                 #novembre
            'Da Pagare',                 #dicembre
            'Da Pagare',                 #gennaio
            'Da Pagare',                 #febbraio
            'Da Pagare',                 #marzo
            'Da Pagare',                 #aprile
            'Da Pagare',                 #maggio
            'Da Pagare',                 #giugno
            'Da Pagare',                 #luglio
            'Da Pagare',                 #agosto
            'Da Pagare',                 #incassare_oltre
            'Da Pagare',                 #totale_da_incassare
            'Da Pagare Scaduti',         #scaduti_30gg
            'Da Pagare Scaduti',         #scaduti_60gg
            'Da Pagare Scaduti',         #scaduti_oltre
            'Da Pagare Scaduti',         #totale_scaduti
            'Totale'                     #totale_attivi
        ],
            passive_df.columns])

        st.markdown("##### PASSIVI")
        st.dataframe(passive_df, use_container_width=True, column_config=column_config, hide_index = True)


    # Since the formatting comes with the Styler object and I cannot use the dataframe without it,
    # I'm recreating the dataframes.
    #
    # If I don't use the styler I don't need the following two lines, but
    # I'll remove the multiindex instead for ease of manipulation.
    #
    # active_df = pd.DataFrame(active_df.data)
    # passive_df = pd.DataFrame(passive_df.data)
    active_df.columns = active_df.columns.droplevel(0)
    passive_df.columns = passive_df.columns.droplevel(0)

    if active_df is not None and passive_df is not None:
        try:
            active_totals = active_df.iloc[[-1]].copy()    # Last row as dataframe
            passive_totals = passive_df.iloc[[-1]].copy()  # Last row as dataframe
            active_totals = active_totals.drop('Cassa', axis=1)
            passive_totals = passive_totals.drop('Cassa', axis=1)

            # TODO: I should test that for every page, especially when the app does not have a lot
            #  of data, that every page looks correct. I could do it with the streamlit app test framework
            #  since it handles searching for elements easier, but I need to check that I can seed the
            #  database correctly.
            #  Also I have to keep testing simple, but doing it with cypress can be problematic, unless
            #  there is a function to test that there is no red color on the screen.
            # Filling nans so that I don't have errors in the saldo calculation below.
            active_totals = active_totals.fillna(0)
            passive_totals = passive_totals.fillna(0)

            saldo_columns = [
                                        # cassa
                'Set',                  # settembre
                'Ott',                  # ottobre
                'Nov',                  # novembre
                'Dic',                  # dicembre
                'Gen',                  # gennaio
                'Feb',                  # febbraio
                'Mar',                  # marzo
                'Apr',                  # aprile
                'Mag',                  # maggio
                'Giu',                  # giugno
                'Lug',                  # luglio
                'Ago',                  # agosto
                'Oltre',                # pagare_oltre
                'Totale',               # totale_da_pagare
                '30GG',                 # scaduti_30gg
                '60GG',                 # scaduti_60gg
                'Oltre ',    # HACK: space in column name for avoiding duplicate # scaduti_oltre
                'Totale ',   # HACK: space in column name for avoiding duplicate # totale_scaduti
                'Netto'                 # totale_passivi
            ]

            saldo = pd.DataFrame(active_totals.values - passive_totals.values,
                                 columns = saldo_columns)
            saldo.insert(0, "Cassa", 'Tutte le Casse')

            # TODO: fix with multiindex
            # saldo = saldo.style.set_properties(
            #     subset=pd.IndexSlice[:, 'Cassa'],
            #     **{'color': '#75777E'}
            # )

            column_config = get_cashflow_column_config(saldo.columns, months)

            saldo.columns = pd.MultiIndex.from_arrays([[
                'FLUSSO DI CASSA',        #cassa
                'Futuro',                 #'Set',
                'Futuro',                 #'Ott',
                'Futuro',                 #'Nov',
                'Futuro',                 #'Dic',
                'Futuro',                 #'Gen',
                'Futuro',                 #'Feb',
                'Futuro',                 #'Mar',
                'Futuro',                 #'Apr',
                'Futuro',                 #'Mag',
                'Futuro',                 #'Giu',
                'Futuro',                 #'Lug',
                'Futuro',                 #'Ago',
                'Futuro',                 #'Oltre',
                'Futuro',                 #'Totale',
                'Scaduto',                #'30GG',
                'Scaduto',                #'60GG',
                'Scaduto',                #'Oltre ',
                'Scaduto',                #'Totale ',
                'Totale'                  #'Netto'
            ],
                saldo.columns])

            st.markdown("##### TOTALE")

            # todo: small, verify if in column config labels I can use markdown for bold.
            # todo: small, verify if I can use spaces to ident MultiIndex labels to the center.
            st.dataframe(saldo, use_container_width=True, hide_index=True,  column_config=column_config)

        except Exception as e:
            st.error(f"Errore nel calcolo del netto: {str(e)}")
            # TODO: in db
            # st.text("Stack trace:")
            # st.text(traceback.format_exc())
    else:
        st.warning("Per visualizzare il riepilogo netto sono necessari sia i dati attivi che passivi")

    active_errors = are_terms_total_congruent(supabase_client, 'fatture_emesse', user_id, 'fe_')
    passive_errors = are_terms_total_congruent(supabase_client, 'fatture_ricevute', user_id, 'fr_')
    discrepancy_errors = active_errors + passive_errors
    if any(discrepancy_errors):
        with st.expander('Avvisi', expanded = False):
            st.error('Le cifre in questa pagina saranno errate fino a quando gli errori qui sotto non verranno corretti.')
            for e in discrepancy_errors:
                st.warning(e)

if __name__ == '__main__':
    main()
