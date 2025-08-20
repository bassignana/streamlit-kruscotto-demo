import streamlit as st
import pandas as pd
from invoice_utils import render_data_table, render_delete_confirmation, render_selectable_dataframe
from invoice_xml_mapping import XML_FIELD_MAPPING as fields_config
from utils import setup_page


def main():

    user_id, supabase_client, page_can_render = setup_page("Elimina Fatture")

    emesse, ricevute = st.tabs(["Elimina Fattura Emessa", "Elimina Fattura Ricevuta"])

    with emesse:
        result = supabase_client.table('fatture_emesse').select('*').execute()

        if not result.data:
            st.warning("Nessun dato disponibile per il periodo selezionato")
        else:
            selection = render_selectable_dataframe(result.data, 'multi-row')
            if selection.selection['rows']:
                df = pd.DataFrame(result.data)
                selected_indexes= selection.selection['rows']
                selected_ids = df.iloc[selected_indexes].loc[:,'id'].to_list()

                render_delete_confirmation(supabase_client, user_id, 'fatture_emesse', fields_config, df, selected_ids)

    with ricevute:
        result = supabase_client.table('fatture_ricevute').select('*').execute()

        if not result.data:
            st.warning("Nessun dato disponibile per il periodo selezionato")
        else:
            selection = render_selectable_dataframe(result.data, 'multi-row')
            if selection.selection['rows']:
                df = pd.DataFrame(result.data)
                selected_indexes= selection.selection['rows']
                selected_ids = df.iloc[selected_indexes].loc[:,'id'].to_list()

                render_delete_confirmation(supabase_client, user_id, 'fatture_ricevute', fields_config, df, selected_ids)

    # selected_id = render_data_table(supabase_client, user_id, 'fatture_emesse', fields_config, 'Fattura emessa', search_enabled=False)
    # if selected_id:
    #     st.write("---")
    #     render_delete_confirmation(supabase_client, user_id, 'fatture_emesse', fields_config, selected_id, 'Fattura emessa')
    # else:
    #     # st.info("👆 Seleziona un record dalla tabella per eliminarlo")
    #     pass


if __name__ == "__main__":
    main()