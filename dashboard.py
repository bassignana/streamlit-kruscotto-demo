import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime

# Sample data for dashboard
def get_dashboard_data():
    return {
        'fatturato': {'vendite': 4500.25, 'acquisti': 2100.50},
        'altri_movimenti': {'attivi': 800.00, 'passivi': 650.75},
        'a_scadere': {'attivo': 1200.30, 'passivo': 950.40},
        'scaduto': {'attivo': 300.00, 'passivo': 180.25},
        'clienti': [
            {'nome': 'BLUENEXT SRL', 'pi': '04228480408', 'dovuto': 2104.00},
            {'nome': 'SCARAGGI Rag. Candido', 'pi': '05484630727', 'dovuto': 262.00},
            {'nome': 'Tech Solutions S.p.A.', 'pi': '12345678901', 'dovuto': 1500.50}
        ]
    }

def create_metric_card(title, value, icon_color="blue"):
    """Create a metric card with title and value"""
    with st.container():
        st.markdown(f"""
        <div style="
            background: white; 
            padding: 1rem; 
            border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
            border-top: 4px solid {icon_color};
        ">
            <h4 style="margin: 0; color: #374151; font-size: 0.9rem; font-weight: 600;">{title}</h4>
            <p style="margin: 0.5rem 0 0 0; color: #1f2937; font-size: 2rem; font-weight: 700;">€ {value:,.2f}</p>
        </div>
        """, unsafe_allow_html=True)

def create_cash_flow_chart():
    """Create cash flow chart"""
    months = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']
    
    fig = go.Figure()
    
    # Sample data - all zeros as in original
    zero_data = [0] * 12
    
    fig.add_trace(go.Scatter(
        x=months, y=zero_data,
        mode='lines+markers',
        name='Scaduto da incassare',
        line=dict(color='#fb923c', width=3),
        marker=dict(size=6)
    ))
    
    fig.add_trace(go.Scatter(
        x=months, y=zero_data,
        mode='lines+markers', 
        name='Scaduto da pagare',
        line=dict(color='#e879f9', width=3),
        marker=dict(size=6)
    ))
    
    fig.add_trace(go.Scatter(
        x=months, y=zero_data,
        mode='lines',
        name='Da incassare',
        line=dict(color='#3bbfad', width=3),
        fill='tonexty',
        fillcolor='rgba(59,191,173,0.3)'
    ))
    
    fig.add_trace(go.Scatter(
        x=months, y=zero_data,
        mode='lines',
        name='Da pagare',
        line=dict(color='#f87171', width=3),
        fill='tonexty',
        fillcolor='rgba(248,113,113,0.3)'
    ))
    
    fig.update_layout(
        title='Flussi di cassa',
        xaxis_title='',
        yaxis_title='Euro',
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        plot_bgcolor='white'
    )
    
    return fig

def create_simple_chart(title, series1_name, series2_name):
    """Create simple area chart for invoices and movements"""
    months = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']
    zero_data = [0] * 12
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=months, y=zero_data,
        mode='lines',
        name=series1_name,
        line=dict(color='#3bbfad', width=3),
        fill='tozeroy',
        fillcolor='rgba(59,191,173,0.3)'
    ))
    
    fig.add_trace(go.Scatter(
        x=months, y=zero_data,
        mode='lines',
        name=series2_name,
        line=dict(color='#f87171', width=3),
        fill='tozeroy',
        fillcolor='rgba(248,113,113,0.3)'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='',
        yaxis_title='',
        height=160,
        showlegend=False,
        plot_bgcolor='white',
        margin=dict(t=40, b=20, l=20, r=20)
    )
    
    return fig

def financial_dashboard():
    """Main dashboard function"""
    st.title("📊 Dashboard Finanziario")
    
    # Get data
    data = get_dashboard_data()
    
    # Top metrics in 2x2 grid
    # First row
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Fatturato (IVA inclusa)")
        subcol1, subcol2 = st.columns(2)
        with subcol1:
            create_metric_card("📈 Vendite", data['fatturato']['vendite'], "#3bbfad")
        with subcol2:
            create_metric_card("📉 Acquisti", data['fatturato']['acquisti'], "#f87171")
    
    with col2:
        st.markdown("### Altri movimenti (IVA inclusa)")
        subcol1, subcol2 = st.columns(2)
        with subcol1:
            create_metric_card("📈 Attivi", data['altri_movimenti']['attivi'], "#3bbfad")
        with subcol2:
            create_metric_card("📉 Passivi", data['altri_movimenti']['passivi'], "#f87171")
    
    # Second row
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("### A scadere")
        subcol1, subcol2 = st.columns(2)
        with subcol1:
            create_metric_card("📈 Attivo", data['a_scadere']['attivo'], "#3bbfad")
        with subcol2:
            create_metric_card("📉 Passivo", data['a_scadere']['passivo'], "#f87171")
    
    with col4:
        st.markdown("### Scaduto")
        subcol1, subcol2 = st.columns(2)
        with subcol1:
            create_metric_card("📈 Attivo", data['scaduto']['attivo'], "#3bbfad")
        with subcol2:
            create_metric_card("📉 Passivo", data['scaduto']['passivo'], "#f87171")
    
    st.write("---")
    
    # Second row with charts and info
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Scadenze section
        st.markdown("### 📅 Scadenze")
        
        tab1, tab2 = st.tabs(["Passate", "Prossime"])
        
        with tab1:
            st.info("Non ci sono scadenze passate")
        
        with tab2:
            st.info("Non ci sono scadenze in arrivo")
    
    with col2:
        # Cash flow chart
        fig = create_cash_flow_chart()
        st.plotly_chart(fig, use_container_width=True)
    
    st.write("---")
    
    # Third row with smaller charts
    col1, col2 = st.columns(2)
    
    with col1:
        fig_fatture = create_simple_chart("Fatture", "Fatture di vendita", "Fatture di acquisto")
        st.plotly_chart(fig_fatture, use_container_width=True)
    
    with col2:
        fig_movimenti = create_simple_chart("Altri movimenti", "Movimenti attivi", "Movimenti passivi")
        st.plotly_chart(fig_movimenti, use_container_width=True)
    
    st.write("---")
    

    st.markdown("### 👥 Clienti")
    
    # Create clients table
    clients_df = pd.DataFrame(data['clienti'])
    
    for _, client in clients_df.iterrows():
        with st.container():
            col_info, col_amount, col_action = st.columns([3, 2, 1])
            
            with col_info:
                st.write(f"**{client['nome']}**")
                st.caption(f"P.I.: {client['pi']}")
            
            with col_amount:
                st.write(f"€ {client['dovuto']:,.2f}")
                # Progress bar (always 0% as in original)
                st.progress(0)
            
            with col_action:
                if st.button("👁️", key=f"view_{client['pi']}", help="Visualizza cliente"):
                    st.info(f"Visualizzazione cliente: {client['nome']}")
            
            st.write("---")
    
    
    st.markdown("### 📢 Comunicazioni")
        
    with st.container():
        st.markdown("#### Kruscotto - Nuove funzionalità")
        st.write("""
        Gentile Utente,
        
        con i prossimi rilasci verranno abilitate le seguenti funzioni:
        - importazione automatica FE attive e passive dallo SDI;
        - gestione del saldo iniziale.
        
        Distinti saluti.
        
        **Area Supporto Kruscotto**
        """)
        
        st.write("---")
        
        st.markdown("#### Importazione Fatture Elettroniche XML")
        st.write("""
        Gentile Utente,
        
        attualmente la piattaforma Kruscotto permette di importare le Fatture Elettroniche XML con le relative scadenze.
        
        Per importare le Fatture Elettroniche procedere come segue:
        
        - cliccare sul nome utente in alto a destra e selezionare la voce Profilo;
        - compilare con i propri dati fiscali i campi Partita IVA e Codice fiscale;
        - cliccare su Salva;
        - selezionare sulla barra di sinistra la voce Fatture;
        - cliccare sulla scritta **clicca qui**;
        - selezionare i file XML delle Fatture Elettroniche (sia attive che passive);
        - confermare l'importazione delle Fatture Elettroniche.
        
        Per domande e chiarimenti potete scrivere a **assistenza@kruscotto.it**
        
        **Area Assistenza**
        """)

def main():
    st.set_page_config(page_title="Dashboard Finanziario", page_icon="📊", layout="wide")
    financial_dashboard()

if __name__ == "__main__":
    main()