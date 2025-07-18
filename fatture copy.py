import streamlit as st
import pandas as pd
from datetime import date, datetime
import uuid
import plotly.graph_objects as go


# Initialize session state for invoices
if 'invoices' not in st.session_state:
    st.session_state.invoices = pd.DataFrame({
        'id': ['inv_001', 'inv_002', 'inv_003'],
        'numero': ['2024-001', '2024-002', '2024-003'],
        'cliente': ['Azienda ABC S.r.l.', 'Studio Legale Rossi', 'Impresa Edile Milano'],
        'divisa': ['EUR - Euro', 'EUR - Euro', 'USD - Dollaro'],
        'importo_totale': [1250.50, 3400.00, 850.75],
        'data_documento': [date(2024, 1, 15), date(2024, 1, 20), date(2024, 1, 25)]
    })

# Available options
CURRENCY_OPTIONS = ['EUR - Euro', 'USD - Dollaro', 'GBP - Sterlina']
CLIENT_OPTIONS = [
    'Azienda ABC S.r.l.',
    'Studio Legale Rossi', 
    'Impresa Edile Milano',
    'Tech Solutions S.p.A.',
    'Consulting Group Ltd',
    'Marketing Plus S.r.l.'
]


def xml_invoice_uploader():
    """File uploader widget for XML invoices"""
    
    uploaded_files = st.file_uploader(
        "Trascina qui la tua fattura in formato XML o *clicca qui* (massimo 20 per volta)",
        type=['xml'],
        accept_multiple_files=True,
        help="Carica fino a 20 fatture XML contemporaneamente"
    )
    
    if uploaded_files:
        st.success(f"📄 {len(uploaded_files)} file caricato/i con successo!")
        
        # Display uploaded files info
        for i, file in enumerate(uploaded_files, 1):
            st.write(f"**{i}.** {file.name} ({file.size} bytes)")
        
        # Process button
        if st.button("🔄 Elabora Fatture", type="primary"):
            with st.spinner("Elaborazione in corso..."):
                # Here you would process the XML files
                st.success("✅ Fatture elaborate con successo!")
    
    return uploaded_files


def add_invoice():
    """Add a new invoice"""
    st.subheader("➕ Aggiungi Nuova Fattura")
    
    with st.form("add_invoice_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            numero = st.text_input("Numero *", placeholder="es. 2024-001")
            cliente = st.selectbox("Cliente *", [""] + CLIENT_OPTIONS)
            divisa = st.selectbox("Divisa *", CURRENCY_OPTIONS, index=0)
        
        with col2:
            importo_totale = st.number_input("Importo totale *", min_value=0.0, step=0.01)
            data_documento = st.date_input("Data *", value=date.today())
        
        submitted = st.form_submit_button("Aggiungi Fattura", type="primary")
        
        if submitted:
            if numero and cliente and importo_totale > 0:
                new_invoice = {
                    'id': f"inv_{uuid.uuid4().hex[:8]}",
                    'numero': numero,
                    'cliente': cliente,
                    'divisa': divisa,
                    'importo_totale': importo_totale,
                    'data_documento': data_documento
                }
                
                # Add to dataframe
                new_row = pd.DataFrame([new_invoice])
                st.session_state.invoices = pd.concat([st.session_state.invoices, new_row], ignore_index=True)
                
                st.success(f"Fattura {numero} aggiunta con successo!")
                st.rerun()
            else:
                st.error("Per favore compila tutti i campi obbligatori")

def search_invoices():
    """Search invoices by client name"""
    st.subheader("🔍 Cerca Fatture")
    
    search_term = st.text_input("Cerca per nome cliente:", placeholder="Inserisci nome cliente...")
    
    if search_term:
        filtered_df = st.session_state.invoices[
            st.session_state.invoices['cliente'].str.contains(search_term, case=False, na=False)
        ]
        
        if not filtered_df.empty:
            st.write(f"Trovate {len(filtered_df)} fatture per '{search_term}':")
            display_df = filtered_df.drop('id', axis=1)  # Hide ID column
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info(f"Nessuna fattura trovata per '{search_term}'")
    else:
        st.info("Inserisci un termine di ricerca per cercare le fatture")

def modify_invoice():
    """Modify an existing invoice"""
    st.subheader("✏️ Modifica Fattura")
    
    if st.session_state.invoices.empty:
        st.info("Nessuna fattura disponibile per la modifica")
        return
    
    # Select invoice to modify
    invoice_options = st.session_state.invoices.apply(
        lambda row: f"{row['numero']} - {row['cliente']}", axis=1
    ).tolist()
    
    selected_invoice = st.selectbox("Seleziona fattura da modificare:", [""] + invoice_options)
    
    if selected_invoice:
        # Get the selected invoice index
        selected_index = invoice_options.index(selected_invoice)
        invoice_data = st.session_state.invoices.iloc[selected_index]
        
        with st.form("modify_invoice_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                numero = st.text_input("Numero *", value=invoice_data['numero'])
                cliente = st.selectbox("Cliente *", CLIENT_OPTIONS, 
                                     index=CLIENT_OPTIONS.index(invoice_data['cliente']) 
                                     if invoice_data['cliente'] in CLIENT_OPTIONS else 0)
                divisa = st.selectbox("Divisa *", CURRENCY_OPTIONS,
                                    index=CURRENCY_OPTIONS.index(invoice_data['divisa']))
            
            with col2:
                importo_totale = st.number_input("Importo totale *", 
                                               value=float(invoice_data['importo_totale']),
                                               min_value=0.0, step=0.01)
                data_documento = st.date_input("Data *", value=invoice_data['data_documento'])
            
            submitted = st.form_submit_button("Aggiorna Fattura", type="primary")
            
            if submitted:
                if numero and cliente and importo_totale > 0:
                    # Update the invoice
                    st.session_state.invoices.loc[selected_index, 'numero'] = numero
                    st.session_state.invoices.loc[selected_index, 'cliente'] = cliente
                    st.session_state.invoices.loc[selected_index, 'divisa'] = divisa
                    st.session_state.invoices.loc[selected_index, 'importo_totale'] = importo_totale
                    st.session_state.invoices.loc[selected_index, 'data_documento'] = data_documento
                    
                    st.success(f"Fattura {numero} aggiornata con successo!")
                    st.rerun()
                else:
                    st.error("Per favore compila tutti i campi obbligatori")

def delete_invoice():
    """Delete an invoice"""
    st.subheader("🗑️ Elimina Fattura")
    
    if st.session_state.invoices.empty:
        st.info("Nessuna fattura disponibile per l'eliminazione")
        return
    
    # Select invoice to delete
    invoice_options = st.session_state.invoices.apply(
        lambda row: f"{row['numero']} - {row['cliente']}", axis=1
    ).tolist()
    
    selected_invoice = st.selectbox("Seleziona fattura da eliminare:", [""] + invoice_options)
    
    if selected_invoice:
        selected_index = invoice_options.index(selected_invoice)
        invoice_data = st.session_state.invoices.iloc[selected_index]
        
        # Show invoice details
        st.write("**Dettagli fattura da eliminare:**")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Numero:** {invoice_data['numero']}")
            st.write(f"**Cliente:** {invoice_data['cliente']}")
        with col2:
            st.write(f"**Importo:** {invoice_data['importo_totale']} {invoice_data['divisa'].split(' - ')[0]}")
            st.write(f"**Data:** {invoice_data['data_documento']}")
        
        st.warning("⚠️ Questa azione non può essere annullata!")
        
        if st.button("Elimina Fattura", type="secondary"):
            st.session_state.invoices = st.session_state.invoices.drop(selected_index).reset_index(drop=True)
            st.success(f"Fattura {invoice_data['numero']} eliminata con successo!")
            st.rerun()

def view_all_invoices():
    """Display all invoices with embedded search"""
    st.subheader("📋 Tutte le Fatture")
    
    if st.session_state.invoices.empty:
        st.info("Nessuna fattura presente nel sistema")
    else:
        # Search filters above the table
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Get unique clients for selectbox with fuzzy search
            unique_clients = sorted(st.session_state.invoices['cliente'].unique().tolist())
            client_filter = st.selectbox(
                "🔍 Filtra per Cliente:",
                ["Tutti i clienti"] + unique_clients,
                index=0,
                help="Inizia a digitare per cercare un cliente specifico"
            )
        
        with col2:
            # Text search for additional filtering
            text_search = st.text_input(
                "🔎 Ricerca testuale:",
                placeholder="Cerca per numero, cliente...",
                help="Cerca in tutti i campi"
            )
        
        # Apply filters
        filtered_df = st.session_state.invoices.copy()
        
        # Client filter
        if client_filter != "Tutti i clienti":
            filtered_df = filtered_df[filtered_df['cliente'] == client_filter]
        
        # Text search filter
        if text_search:
            mask = (
                filtered_df['numero'].astype(str).str.contains(text_search, case=False, na=False) |
                filtered_df['cliente'].astype(str).str.contains(text_search, case=False, na=False) |
                filtered_df['divisa'].astype(str).str.contains(text_search, case=False, na=False)
            )
            filtered_df = filtered_df[mask]
        
        # Display summary statistics for filtered data
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_invoices = len(filtered_df)
            st.metric("Fatture Mostrate", f"{total_invoices}/{len(st.session_state.invoices)}")
        with col2:
            if not filtered_df.empty:
                total_amount = filtered_df['importo_totale'].sum()
                st.metric("Importo Totale", f"€ {total_amount:,.2f}")
            else:
                st.metric("Importo Totale", "€ 0,00")
        with col3:
            if not filtered_df.empty:
                unique_clients_filtered = filtered_df['cliente'].nunique()
                st.metric("Clienti Unici", unique_clients_filtered)
            else:
                st.metric("Clienti Unici", "0")
        with col4:
            if not filtered_df.empty:
                avg_amount = filtered_df['importo_totale'].mean()
                st.metric("Importo Medio", f"€ {avg_amount:,.2f}")
            else:
                st.metric("Importo Medio", "€ 0,00")
        
        st.write("---")
        
        # Display filtered results
        if filtered_df.empty:
            st.warning("Nessuna fattura corrisponde ai criteri di ricerca selezionati")
        else:
            # Display dataframe without ID column
            display_df = filtered_df.drop('id', axis=1)
            st.dataframe(display_df, use_container_width=True)
            
            # Show filter summary if filters are active
            if client_filter != "Tutti i clienti" or text_search:
                st.caption(f"📊 Mostrando {len(filtered_df)} di {len(st.session_state.invoices)} fatture totali")


def create_monthly_summary():
    """Create monthly summary table like the HTML structure"""
    
    # Sample data - replace with your actual session state data
    sales_monthly = {1: 1250.50, 2: 3400.00, 3: 850.75}  # st.session_state.sales_invoices
    purchase_monthly = {1: 780.00, 2: 1200.50, 3: 450.25}  # st.session_state.purchase_invoices
    
    months = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']
    
    # Create table data with all three rows in one table
    summary_data = {'': ['Fatture di Vendita', 'Fatture di Acquisto', 'Saldo']}
    saldo_row = []
    
    for i, month in enumerate(months, 1):
        sales = sales_monthly.get(i, 0.0)
        purchase = purchase_monthly.get(i, 0.0)
        balance = sales - purchase
        
        summary_data[month] = [f"{sales:,.2f}", f"{purchase:,.2f}", f"{balance:,.2f}"]
        saldo_row.append(balance)
    
    df = pd.DataFrame(summary_data)
    
    return df, saldo_row

def view_financial_summary():
    """Display financial summary tab"""
    st.subheader("📊 Riepilogo Finanziario")
    
    # Create summary table
    summary_df, saldo_data = create_monthly_summary()
    
    # Display the complete table with saldo included
    st.dataframe(summary_df.set_index(''), use_container_width=True)
    
    # Create chart
    months = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']
    sales_data = [1250.50, 3400.00, 850.75] + [0] * 9  # Sample data
    purchase_data = [780.00, 1200.50, 450.25] + [0] * 9  # Sample data
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Fatture di Vendita',
        x=months,
        y=sales_data,
        marker_color='rgb(56, 189, 248)',
        opacity=0.85
    ))
    
    fig.add_trace(go.Bar(
        name='Fatture di Acquisto',
        x=months,
        y=purchase_data,
        marker_color='rgb(74, 222, 128)',
        opacity=0.85
    ))
    
    fig.update_layout(
        title='Andamento Mensile',
        xaxis_title='',
        yaxis_title='Euro',
        barmode='group',
        height=400,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    total_sales = sum(sales_data)
    total_purchases = sum(purchase_data)
    net_balance = total_sales - total_purchases
    
    with col1:
        st.metric("Totale Vendite", f"€ {total_sales:,.2f}")
    with col2:
        st.metric("Totale Acquisti", f"€ {total_purchases:,.2f}")
    with col3:
        st.metric("Saldo Netto", f"€ {net_balance:,.2f}")


# Usage in your main app:



# Main App
def main():
    st.set_page_config(page_title="Sistema Gestione Fatture", page_icon="📄", layout="wide")
    
    st.title("📄 Sistema Gestione Fatture")
    uploaded_files = xml_invoice_uploader()

    tab1, tab2, tab3 = st.tabs([
        "💰 Fatture di Vendita", 
        "🛒 Fatture di Acquisto", 
        "📊 Riepilogo Finanziario"
    ])

    with tab1:
        st.write("Gestisci le tue fatture: aggiungi, modifica, elimina e cerca facilmente")
        
        # Always show all invoices at the top
        view_all_invoices()
        
        st.write("---")
        
        # Action menu below the table
        st.subheader("🛠️ Operazioni")
        
        # Horizontal menu with columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("➕ Aggiungi Fattura", use_container_width=True):
                st.session_state.show_section = "add"
        
        with col2:
            if st.button("✏️ Modifica Fattura", use_container_width=True):
                st.session_state.show_section = "modify"
        
        with col3:
            if st.button("🗑️ Elimina Fattura", use_container_width=True):
                st.session_state.show_section = "delete"
        
        # Initialize session state for section display
        if 'show_section' not in st.session_state:
            st.session_state.show_section = None
        
        # Show selected section
        if st.session_state.show_section == "add":
            st.write("---")
            add_invoice()
            if st.button("❌ Chiudi", key="close_add"):
                st.session_state.show_section = None
                st.rerun()
        
        elif st.session_state.show_section == "modify":
            st.write("---")
            modify_invoice()
            if st.button("❌ Chiudi", key="close_modify"):
                st.session_state.show_section = None
                st.rerun()
        
        elif st.session_state.show_section == "delete":
            st.write("---")
            delete_invoice()
            if st.button("❌ Chiudi", key="close_delete"):
                st.session_state.show_section = None
                st.rerun()
        
        # Footer
        if st.session_state.show_section is None:
            st.write("---")
            st.info("💡 **Suggerimento:** Usa la ricerca per trovare rapidamente le fatture di un cliente specifico")

    with tab2:
        
    with tab3:
        view_financial_summary()

if __name__ == "__main__":
    main()