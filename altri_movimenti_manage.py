import streamlit as st
from altri_movimenti_utils import render_movimenti_crud_page
from utils import setup_page, create_monthly_line_chart
from altri_movimenti_config import altri_movimenti_config
import pandas as pd

def main():
    user_id, supabase_client, page_can_render = setup_page("Gestione Altri Movimenti")
    sommario, attivi, passivi = st.tabs(["Sommario", "Movimenti Attivi", "Movimenti Passivi"])

    if page_can_render:

        with sommario:
            # TODO; .eq('user_id', user_id) AM I ENFORCING THIS because the view will
            #  only select only the user's data?
            result = supabase_client.table('monthly_altri_movimenti_summary').select('*').execute()

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

                fig = create_monthly_line_chart(df,"Movimenti Attivi", "Movimenti Passivi")
                st.plotly_chart(fig)


        with attivi:
            render_movimenti_crud_page(supabase_client, user_id,
                                       'movimenti_attivi', 'ma_',
                                       'rma_',
                                       altri_movimenti_config)
        with passivi:
            render_movimenti_crud_page(supabase_client, user_id,
                                       'movimenti_passivi', 'mp_',
                                       'rmp_',
                                       altri_movimenti_config)

if __name__ == '__main__':
    main()

