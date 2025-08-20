import streamlit as st
from invoice_xml_mapping import XML_FIELD_MAPPING as fields_config
from invoice_utils import  render_data_table, render_modify_form
from utils import setup_page
import pandas as pd


def main():
    # st.subheader('Modifica Fatture')

    user_id, supabase_client, page_can_render = setup_page("Modifica Fatture")

    emesse, ricevute = st.tabs(["Modifica Fattura Emessa", "Modifica Fattura Ricevuta"])

    with emesse:

        # TODO; .eq('user_id', user_id) AM I ENFORCING THIS?
        result = supabase_client.table('fatture_emesse').select('*').execute()

        if not result.data:
            st.warning("Nessun dato disponibile per il periodo selezionato")
        else:
            #TODO: value formatting
            df = pd.DataFrame(result.data)

            # Assumning that I force the first column of the view to be the index one.
            # df = df.set_index(df.columns[0])
            # TODO; df.columns = ["Voce"] + df.columns[1:]

            df.columns = [
                col.replace('_', ' ').title() if isinstance(col, str) else str(col)
                for col in df.columns
            ]

            # TODO: scroll bar always preset, auto formatting everything to euro, remove some options.
            st_df = st.dataframe(df, use_container_width=True, selection_mode = 'single-row', on_select='rerun')

            if st_df.selection['rows']:
                selected_index = st_df.selection['rows'][0]

                selected_id = df.loc[selected_index, 'Id']
                # TODO: to persist this I need to persist the return value in session state?
                render_modify_form(supabase_client, user_id, 'fatture_emesse', fields_config, df, selected_id, 'fe_')


    with ricevute:

        # TODO; .eq('user_id', user_id) AM I ENFORCING THIS?
        result = supabase_client.table('fatture_ricevute').select('*').execute()

        if not result.data:
            st.warning("Nessun dato disponibile per il periodo selezionato")
        else:
            #TODO: value formatting
            df = pd.DataFrame(result.data)

            # Assumning that I force the first column of the view to be the index one.
            # df = df.set_index(df.columns[0])
            # TODO; df.columns = ["Voce"] + df.columns[1:]

            df.columns = [
                col.replace('_', ' ').title() if isinstance(col, str) else str(col)
                for col in df.columns
            ]

            # TODO: scroll bar always preset, auto formatting everything to euro, remove some options.
            st_df = st.dataframe(df, use_container_width=True, selection_mode = 'single-row', on_select='rerun')

            if st_df.selection['rows']:
                selected_index = st_df.selection['rows'][0]
                # TODO: why the capitol 'I' in Id?
                selected_id = df.loc[selected_index, 'Id']
                # TODO: to persist this I need to persist the return value in session state?
                render_modify_form(supabase_client, user_id, 'fatture_ricevute', fields_config, df, selected_id, 'fr_')

if __name__ == "__main__":
    main()