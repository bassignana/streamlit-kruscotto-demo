import streamlit as st
import pandas as pd
from decimal import Decimal, getcontext
from datetime import date, datetime
import plotly.graph_objects as go
from dateutil.relativedelta import relativedelta

getcontext().prec = 2

def get_invoices_statistics(supabase_client, user_id):
    """Get overview of all invoices and their terms status"""
    try:
        # todo: use count if I don't need the full data.
        emesse_result = supabase_client.table('fatture_emesse').select('id').eq('user_id', user_id).execute()
        emesse_invoices = emesse_result.data or []
        emesse_invoices_count = len(emesse_invoices)

        ricevute_result = supabase_client.table('fatture_ricevute').select('id').eq('user_id', user_id).execute()
        ricevute_invoices = ricevute_result.data or []
        ricevute_invoices_count = len(ricevute_invoices)

        total_invoices_count = emesse_invoices_count + ricevute_invoices_count

        emesse_with_terms_result = supabase_client.table('rate_fatture_emesse').select('DISTINCT invoice_id').eq('user_id', user_id).execute()
        emesse_with_terms = emesse_with_terms_result.data or []
        emesse_with_terms_count = len(emesse_with_terms)

        ricevute_with_terms_result = supabase_client.table('rate_fatture_ricevute').select('DISTINCT invoice_id').eq('user_id', user_id).execute()
        ricevute_with_terms = ricevute_with_terms_result.data or []
        ricevute_with_terms_count = len(ricevute_with_terms)

        invoices_without_terms_count = total_invoices_count - emesse_with_terms_count - ricevute_with_terms_count

        return {
            'total_invoices_count': total_invoices_count,
            'invoices_without_terms_count': invoices_without_terms_count,
        }

    except Exception as e:
        st.error(f"Errore nel caricamento dell'overview: {str(e)}")
        return {
            'total_invoices_count': 0,
            'invoices_without_terms': 0,
        }

def get_monthly_terms_projection(supabase_client, user_id, months_ahead = 12):
    """Get monthly projection of payment terms for next 12 months

    Using datetime.date format, so dealing with int representation of year, month, day:

    date.today()
    datetime.date(2025, 8, 1)


    """
    try:

        today = date.today()
        start_date = today.replace(day=1)  # First day of current month
        end_date = start_date.replace(year=start_date.year + 1)

        # end_date = start_date + relativedelta(months=months_ahead)

        # Load payment terms within the date range
        # terms_result = supabase_client.table('payment_terms').select('''
        #     data_scadenza_pagamento, amount, invoice_id
        # ''').eq('user_id', user_id).gte('data_scadenza_pagamento', start_date.isoformat()).lt('data_scadenza_pagamento', end_date.isoformat()).execute()
        #
        # terms_data = terms_result.data or []

        emesse_terms_result = supabase_client.table('rate_fatture_emesse').select('''
            data_scadenza_pagamento, importo_pagamento_rata
        ''').eq('user_id', user_id).gte('data_scadenza_pagamento', start_date.isoformat()).lt('data_scadenza_pagamento', end_date.isoformat()).execute()
        emesse_terms = emesse_terms_result.data or []

        ricevute_terms_result = supabase_client.table('rate_fatture_ricevute').select('''
            data_scadenza_pagamento, importo_pagamento_rata
        ''').eq('user_id', user_id).gte('data_scadenza_pagamento', start_date.isoformat()).lt('data_scadenza_pagamento', end_date.isoformat()).execute()
        ricevute_terms = ricevute_terms_result.data or []


        month_begin = start_date.month
        for m in range(months_ahead):
            month_begin += m



        # Load invoice data to determine type
        emesse_result = supabase_client.table('fatture_emesse').select('id').eq('user_id', user_id).execute()
        ricevute_result = supabase_client.table('fatture_ricevute').select('id').eq('user_id', user_id).execute()

        emesse_ids = set(inv['id'] for inv in (emesse_result.data or []))
        ricevute_ids = set(inv['id'] for inv in (ricevute_result.data or []))

        # Create monthly projections
        monthly_data = []
        current_saldo = Decimal('0')  # Starting balance

        for i in range(months_ahead):
            month_date = start_date + relativedelta(months=i)
            month_year = month_date.strftime('%Y-%m')
            month_name = month_date.strftime('%b %Y')

            # Calculate totals for this month
            emesse_total = Decimal('0')
            ricevute_total = Decimal('0')

            for term in terms_data:
                term_date = datetime.strptime(term['data_scadenza_pagamento'], '%Y-%m-%d').date()
                term_month = term_date.strftime('%Y-%m')

                if term_month == month_year:
                    amount = Decimal(str(term['importo_pagamento_rata']))
                    if term['invoice_id'] in emesse_ids:
                        emesse_total += amount
                    elif term['invoice_id'] in ricevute_ids:
                        ricevute_total += amount

            # Calculate running balance (saldo)
            # Saldo = previous saldo + emesse (incoming) - ricevute (outgoing)
            current_saldo = current_saldo + emesse_total - ricevute_total

            monthly_data.append({
                'month': month_name,
                'month_date': month_date,
                'emesse_total': float(emesse_total),
                'ricevute_total': float(ricevute_total),
                'saldo': float(current_saldo)
            })

        return pd.DataFrame(monthly_data)

    except Exception as e:
        st.error(f"Errore nel calcolo delle proiezioni mensili: {str(e)}")
        return pd.DataFrame()

def render_overview_metrics(overview_data):
    """Render the overview metrics cards"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "📊 Fatture Totali",
            overview_data['total_invoices'],
            help="Numero totale di fatture (emesse + ricevute)"
        )

    with col2:
        st.metric(
            "📤 Fatture Emesse",
            overview_data['emesse_invoices'],
            help="Numero di fatture emesse"
        )

    with col3:
        st.metric(
            "📥 Fatture Ricevute",
            overview_data['ricevute_invoices'],
            help="Numero di fatture ricevute"
        )

    # with col4:
    #     percentage = overview_data['percentage_with_terms']
    #     st.metric(
    #         "✅ Con Scadenze",
    #         f"{overview_data['invoices_with_terms']} ({percentage:.1f}%)",
    #         help="Fatture con scadenze di pagamento configurate"
    #     )

def render_terms_status_breakdown(overview_data):
    """Render breakdown of invoices with/without terms"""
    # st.markdown("### 📋 Stato Configurazione Scadenze")

    col1, col2 = st.columns([2, 1])

    with col1:
        # Create pie chart
        labels = ['Con Scadenze', 'Senza Scadenze']
        values = [overview_data['invoices_with_terms'], overview_data['invoices_without_terms']]
        colors = ['#00CC88', '#FF6B6B']

        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            marker_colors=colors,
            hole=0.4,
            textinfo='label+percent+value',
            texttemplate='%{label}<br>%{value} fatture<br>(%{percent})'
        )])

        fig.update_layout(
            title="Distribuzione Configurazione Scadenze",
            showlegend=True,
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### 📈 Statistiche")

        total = overview_data['total_invoices']
        with_terms = overview_data['invoices_with_terms']
        without_terms = overview_data['invoices_without_terms']

        if total > 0:
            st.metric("Configurate", f"{with_terms}/{total}", f"{with_terms/total*100:.1f}%")
            st.metric("Da Configurare", f"{without_terms}/{total}", f"{without_terms/total*100:.1f}%")

            if without_terms > 0:
                st.warning(f"⚠️ {without_terms} fatture necessitano configurazione scadenze")
            else:
                st.success("🎉 Tutte le fatture hanno scadenze configurate!")
        else:
            st.info("Nessuna fattura presente nel sistema")

def render_monthly_projection_table(monthly_df: pd.DataFrame):
    """Render the monthly projection table"""
    if monthly_df.empty:
        st.info("📊 Nessuna scadenza di pagamento nei prossimi 12 mesi")
        return

    st.markdown("### Proiezione Fatture Prossimi 12 Mesi")

    # Create the transposed table data (rows become columns)
    table_data = {
        '': ['Scadenze Emesse (€)', 'Scadenze Ricevute (€)', 'Saldo Cumulativo (€)']
    }

    # Add each month as a column
    for _, row in monthly_df.iterrows():
        month_name = row['month']
        table_data[month_name] = [
            f"{row['emesse_total']:,.2f}",
            f"{row['ricevute_total']:,.2f}",
            f"{row['saldo']:,.2f}"
        ]

    display_df = pd.DataFrame(table_data)

    # Style the dataframe
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    # Summary metrics
    # st.markdown("#### 📊 Riepilogo Periodo")
    # col1, col2, col3, col4 = st.columns(4)
    #
    # total_emesse = monthly_df['emesse_total'].sum()
    # total_ricevute = monthly_df['ricevute_total'].sum()
    # final_saldo = monthly_df['saldo'].iloc[-1] if len(monthly_df) > 0 else 0
    # net_flow = total_emesse - total_ricevute
    #
    # with col1:
    #     st.metric("💰 Totale Entrate", f"€ {total_emesse:,.2f}")
    # with col2:
    #     st.metric("💸 Totale Uscite", f"€ {total_ricevute:,.2f}")
    # with col3:
    #     delta_color = "normal" if net_flow >= 0 else "inverse"
    #     st.metric("📈 Flusso Netto", f"€ {net_flow:,.2f}", delta_color=delta_color)
    # with col4:
    #     saldo_color = "normal" if final_saldo >= 0 else "inverse"
    #     st.metric("🏦 Saldo Finale", f"€ {final_saldo:,.2f}", delta_color=saldo_color)

def render_monthly_charts(monthly_df: pd.DataFrame):
    """Render charts for monthly projections"""
    if monthly_df.empty:
        return

    # st.markdown("### 📈 Grafici Andamento")

    col1, col2 = st.columns(2)

    with col1:
        # Cash flow chart
        fig1 = go.Figure()

        fig1.add_trace(go.Bar(
            name='Entrate (Emesse)',
            x=monthly_df['month'],
            y=monthly_df['emesse_total'],
            marker_color='#00CC88'
        ))

        fig1.add_trace(go.Bar(
            name='Uscite (Ricevute)',
            x=monthly_df['month'],
            y=[-amount for amount in monthly_df['ricevute_total']],  # Negative for visual effect
            marker_color='#FF6B6B'
        ))

        fig1.update_layout(
            title='Flussi di Cassa Mensili',
            xaxis_title='Mese',
            yaxis_title='Importo (€)',
            barmode='relative',
            height=400
        )

        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        # Cumulative balance line chart
        fig2 = go.Figure()

        fig2.add_trace(go.Scatter(
            x=monthly_df['month'],
            y=monthly_df['saldo'],
            mode='lines+markers',
            name='Saldo Cumulativo',
            line=dict(color='#4A90E2', width=3),
            marker=dict(size=8)
        ))

        # Add zero line
        fig2.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Pareggio")

        fig2.update_layout(
            title='Saldo Cumulativo',
            xaxis_title='Mese',
            yaxis_title='Saldo (€)',
            height=400
        )

        st.plotly_chart(fig2, use_container_width=True)

def main():

    st.set_page_config(
        page_title="Riepilogo Fatture",
        page_icon="📊",
        layout="wide"
    )

    getcontext().prec = 2

    if 'user' not in st.session_state or not st.session_state.user:
        st.error("🔐 Effettuare il login per accedere a questa pagina")
        st.stop()

    user_id = st.session_state.user.id

    if 'client' not in st.session_state:
        st.error("❌ Errore di connessione al database")
        st.stop()

    supabase_client = st.session_state.client

    # Load data
    with st.spinner("📊 Caricamento dati..."):
        invoices_statistics = get_invoices_statistics(supabase_client, user_id)
        monthly_df = get_monthly_terms_projection(supabase_client, user_id)

    # Render terms status breakdown
    if invoices_statistics['total_invoices_count'] > 0:
        render_monthly_projection_table(monthly_df)
        st.markdown("---")
        render_monthly_charts(monthly_df)

        without_terms = invoices_statistics['invoices_without_terms_count']
        if without_terms > 0:
            st.warning(f"""{without_terms} fatture sono sprovviste di scadenze.
Solo le fatture con scadenze configurate saranno prese in considerazione
per il riepilogo presente in questa pagina.""")

    else:
        st.markdown("""
        Per vedere la dashboard completa:
        1. 📄 Crea alcune fatture (emesse o ricevute)
        2. ⏰ Configura le scadenze di pagamento
        3. 📊 Torna qui per vedere l'analisi completa
        """)

if __name__ == "__main__":
    main()