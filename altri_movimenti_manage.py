from decimal import Decimal, ROUND_HALF_UP
import plotly.graph_objects as go
from datetime import datetime
import streamlit as st
from utils import setup_page
import pandas as pd

from altri_movimenti_config import altri_movimenti_config
from altri_movimenti_utils import render_movimenti_crud_page
from utils import money_to_string, to_money


# TODO: The problem here is that I add a lot of complexity
#  because I have to stop the streamlit execution when the
#  dialog is open and manually rerun() everything; but I
#  have to handle the fact that, at the rerun() point, every
#  variable that needs to be present in session_state is
#  up to date. For now I'll search for an easier solution.
def return_warning_modal(message, key):
    """
    Usage:
    is_modal_required, show_warning_modal = return_warning_modal(
                        message = "Tutti gli importi verranno reimpostati, procedere?",
                        key = 'reimposta_importi_movimenti')

                    if is_modal_required:
                        show_warning_modal()
    """
    is_modal_required = True

    unique_key = 'remember_dialog_' + key
    if unique_key not in st.session_state:
        st.session_state.unique_key = True

    if st.session_state.unique_key:

        @st.dialog('Attenzione')
        def show_warning_dialog():
            st.warning(message)

            if st.button('Procedi', key = unique_key + 'Procedi'):
                return True
            if st.button('Annulla', key = unique_key + 'Annulla'):
                return False

            if st.checkbox("Non ricordarmelo più"):
                st.session_state.unique_key = False

        return is_modal_required, show_warning_dialog

    else:
        is_modal_required = False
        return is_modal_required, None

def create_monthly_movements_summary_chart(data_dict, show_amounts=False):

    # Extract months and values
    months = list(data_dict.keys())
    movimenti_attivi = []
    movimenti_passivi = []

    # Use Decimal for precise financial calculations
    for month in months:
        attivi = Decimal(str(data_dict[month]['Movimenti Attivi']))
        passivi = Decimal(str(data_dict[month]['Movimenti Passivi']))

        # Round to 2 decimal places using banker's rounding
        attivi_rounded = float(attivi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        passivi_rounded = float(passivi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

        movimenti_attivi.append(attivi_rounded)
        movimenti_passivi.append(passivi_rounded)

    # Create the figure
    fig = go.Figure()

    # Add Movimenti Attivi (Active Movements) - Green bars
    fig.add_trace(go.Bar(
        name='Movimenti Attivi',
        x=months,
        y=movimenti_attivi,
        marker_color='#16a34a',  # Green color
        opacity=0.85,
        text=[f'€ {val:,.2f}' if val != 0 else '' for val in movimenti_attivi] if show_amounts else None,
        textposition='outside' if show_amounts else None,
        textfont=dict(size=10, color='#16a34a') if show_amounts else None,
        hovertemplate='<b>%{fullData.name}</b><br>' +
                      'Mese: %{x}<br>' +
                      'Importo: € %{y:,.2f}<extra></extra>'
    ))

    # Add Movimenti Passivi (Passive Movements) - Red bars
    fig.add_trace(go.Bar(
        name='Movimenti Passivi',
        x=months,
        y=movimenti_passivi,
        marker_color='#dc2626',  # Red color
        opacity=0.85,
        text=[f'€ {val:,.2f}' if val != 0 else '' for val in movimenti_passivi] if show_amounts else None,
        textposition='outside' if show_amounts else None,
        textfont=dict(size=10, color='#dc2626') if show_amounts else None,
        hovertemplate='<b>%{fullData.name}</b><br>' +
                      'Mese: %{x}<br>' +
                      'Importo: € %{y:,.2f}<extra></extra>'
    ))

    # Update layout
    fig.update_layout(
        title={
            'text': 'Movimenti Mensili',
            'font': {'size': 16, 'color': '#1f2937'},
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='Mesi',
        yaxis_title='Importo (€)',
        barmode='group',  # Groups bars side by side
        height=500,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=12)
        ),
        plot_bgcolor='white',  # White background
        paper_bgcolor='white',  # White background
        xaxis=dict(
            showgrid=False,  # Remove grid
            showline=True,
            linewidth=1,
            linecolor='rgba(128,128,128,0.3)'
        ),
        yaxis=dict(
            showgrid=False,  # Remove grid
            showline=True,
            linewidth=1,
            linecolor='rgba(128,128,128,0.3)',
            tickformat=',.0f'
        ),
        margin=dict(t=80, b=40, l=60, r=40)
    )

    # Disable zoom and pan interactions
    fig.update_layout(
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True)
    )

    return fig

def main():
    user_id, supabase_client, page_can_render = setup_page("Gestione Altri Movimenti")
    sommario, attivi, passivi = st.tabs(["Sommario", "Movimenti Attivi", "Movimenti Passivi"])

    if page_can_render:

        with sommario:
            result = supabase_client.table('monthly_altri_movimenti_summary').select('*').execute()

            if not result.data:
                st.warning("Nessun dato disponibile per il periodo selezionato")
            else:

                df = pd.DataFrame(result.data)
                df.columns = [
                    col.replace('_', ' ').title() if isinstance(col, str) else str(col)
                    for col in df.columns
                ]
                df = df.set_index(df.columns[0])


                c1, c2 = st.columns([1,2])

                with c1:
                    m1, m2 = st.columns([1,1])
                    current_month_index = datetime.now().month - 1

                    def get_df_metric(label, amount):
                        with st.container():
                            st.dataframe(
                                pd.DataFrame({label: to_money(amount)},
                                             index = [0]),
                                hide_index = True)

                    with m1:
                            movimenti_attivi_totale = df.loc['Movimenti Attivi',:].iloc[:current_month_index + 1].sum()
                            # st.metric('Totale Movimenti Attivi (€)', money_to_string(movimenti_attivi_totale), border=True)
                            get_df_metric('Totale Movimenti Attivi (€)', movimenti_attivi_totale)

                            current_month_attivi = df.loc['Movimenti Attivi'].iloc[current_month_index]
                            # st.metric('Movimenti Attivi Mese Attuale (€)', money_to_string(current_month_attivi), border=True)
                            get_df_metric('Movimenti Attivi Mese Attuale (€)', current_month_attivi)

                    with m2:
                            movimenti_passivi_totale = df.loc['Movimenti Passivi',:].iloc[:current_month_index + 1].sum()
                            # st.metric('Totale Movimenti Passivi (€)',money_to_string(movimenti_passivi_totale), border=True)
                            get_df_metric('Totale Movimenti Passivi (€)', movimenti_passivi_totale)

                            current_month_passivi = df.loc['Movimenti Passivi'].iloc[current_month_index]
                            # st.metric('Movimenti Passivi Mese Attuale (€)', money_to_string(current_month_passivi), border=True)
                            get_df_metric('Movimenti Passivi Mese Attuale (€)', current_month_passivi)

                with c2:
                    # fig = create_monthly_line_chart(df,"Movimenti Attivi", "Movimenti Passivi")
                    fig = create_monthly_movements_summary_chart(df.to_dict(), show_amounts=False)
                    st.plotly_chart(fig)

                st.dataframe(df, use_container_width=True)


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

