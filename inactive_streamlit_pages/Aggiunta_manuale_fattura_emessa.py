import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import uuid
import plotly.graph_objects as go
import invoice_xml_processor

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

# Initialize payment terms
if 'payment_terms' not in st.session_state:
    st.session_state.payment_terms = pd.DataFrame({
        'id': ['term_001', 'term_002', 'term_003'],
        'invoice_id': ['inv_001', 'inv_001', 'inv_002'],
        'data_scadenza': [date(2024, 2, 15), date(2024, 3, 15), date(2024, 2, 20)],
        'importo': [625.25, 625.25, 3400.00],
        'modalita_pagamento': ['Bonifico', 'Bonifico', 'Bonifico'],
        'cassa': ['Banca Intesa', 'Banca Intesa', 'Banca Intesa'],
        'pagata': [False, False, False]
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
PAYMENT_METHODS = ['Bonifico', 'Contanti', 'Assegno', 'Carta di credito', 'RID', 'Altro']
CASH_ACCOUNTS = ['Banca Intesa', 'Cassa Contanti', 'Cassa Generica', 'INTESA SAN PAOLO']    

def add_payment_term():
    """Add a new payment term to the current list"""
    if 'current_payment_terms' not in st.session_state:
        st.session_state.current_payment_terms = []
    
    new_term = {
        'id': len(st.session_state.current_payment_terms),
        'data_scadenza': date.today() + timedelta(days=30),
        'importo': 0.0,
        'modalita_pagamento': 'Bonifico',
        'cassa': 'Banca Intesa',
        'note': ''
    }
    st.session_state.current_payment_terms.append(new_term)

def remove_payment_term(index):
    """Remove a payment term from the current list"""
    if 0 <= index < len(st.session_state.current_payment_terms):
        st.session_state.current_payment_terms.pop(index)
        st.rerun()

def auto_split_payment(total_amount, num_installments, start_date, interval_days=30):
    """Automatically split payment into equal installments"""
    if num_installments <= 0:
        return
    
    amount_per_installment = total_amount / num_installments
    st.session_state.current_payment_terms = []
    
    for i in range(num_installments):
        new_term = {
            'id': i,
            'data_scadenza': start_date + timedelta(days=interval_days * (i + 1)),
            'importo': round(amount_per_installment, 2),
            'modalita_pagamento': 'Bonifico',
            'cassa': 'Banca Intesa',
            'note': f'Rata {i + 1} di {num_installments}'
        }
        st.session_state.current_payment_terms.append(new_term)

    total_configured = sum(term['importo'] for term in st.session_state.current_payment_terms)
    remaining = total_amount - total_configured
    
    if remaining != 0:
        for term in st.session_state.current_payment_terms:
            if term['id'] == num_installments - 1:
                term['importo'] += remaining

def payment_terms_manager(total_amount, invoice_date):
    """Component to manage payment terms"""
    # st.subheader("💰 Scadenze di Pagamento")
    
    if 'current_payment_terms' not in st.session_state:
        st.session_state.current_payment_terms = []    
    
    # Quick setup options
    with st.expander("⚡ Configurazione Rapida", expanded=True):
        # col1, col2, col3 = st.columns(3)
        
        # with col1:
        #     if st.button("📅 Pagamento Unico", use_container_width=True):
        #         st.session_state.current_payment_terms = [{
        #             'id': 0,
        #             'data_scadenza': invoice_date + timedelta(days=30),
        #             'importo': total_amount,
        #             'modalita_pagamento': 'Bonifico',
        #             'cassa': 'Banca Intesa',
        #             'note': 'Pagamento unico'
        #         }]
        #         st.rerun()
        
        # with col2:
        #     if st.button("📊 2 Rate Mensili", use_container_width=True):
        #         auto_split_payment(total_amount, 2, invoice_date, 30)
        #         st.rerun()
        
        # with col3:
        #     if st.button("📈 3 Rate Mensili", use_container_width=True):
        #         auto_split_payment(total_amount, 3, invoice_date, 30)
        #         st.rerun()
        
        # Custom split
        st.markdown("**Configurazione Personalizzata:**")
        split_col1, split_col2, split_col3 = st.columns([2, 2, 1])
        
        with split_col1:
            num_installments = st.number_input("Numero rate", min_value=1, max_value=12, value=1)
        
        with split_col2:
            interval_days = st.number_input("Giorni tra rate", min_value=1, max_value=365, value=30)
        
        with split_col3:
            if st.button("🔄 Applica Configurazione", use_container_width=True):
                auto_split_payment(total_amount, num_installments, invoice_date, interval_days)
                st.rerun()
    
    # Current payment terms
    if st.session_state.current_payment_terms:
        st.markdown("### 📋 Scadenze Configurate")
        
        total_configured = sum(term['importo'] for term in st.session_state.current_payment_terms)
        remaining = total_amount - total_configured
        
        # Summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Importo Totale", f"€ {total_amount:,.2f}")
        with col2:
            st.metric("Importo Configurato", f"€ {total_configured:,.2f}")
        with col3:
            st.metric("Rimanente", f"€ {remaining:,.2f}")
            if abs(remaining) >= 0.01:
                st.warning(f"⚠️ Differenza di € {remaining:,.2f}")
        
        # Payment terms list
        for i, term in enumerate(st.session_state.current_payment_terms):
            with st.container():
                st.markdown(f"#### 💳 Scadenza {i + 1}")
                
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                
                with col1:
                    new_date = st.date_input(
                        "Data Scadenza",
                        value=term['data_scadenza'],
                        key=f"date_{i}"
                    )
                    st.session_state.current_payment_terms[i]['data_scadenza'] = new_date
                
                with col2:
                    new_amount = st.number_input(
                        "Importo (€)",
                        min_value=0.0,  # Changed from 0.01 to 0.0
                        value=max(0.0, float(term['importo'])),  # Ensure value is not negative
                        step=0.01,
                        key=f"amount_{i}"
                    )
                    st.session_state.current_payment_terms[i]['importo'] = new_amount

                with col3:
                    new_payment_method = st.selectbox(
                        "Modalità",
                        PAYMENT_METHODS,
                        index=PAYMENT_METHODS.index(term['modalita_pagamento']),
                        key=f"method_{i}"
                    )
                    st.session_state.current_payment_terms[i]['modalita_pagamento'] = new_payment_method

                with col4:
                    st.write("")  # Spacing
                    st.write("")  # Spacing
                    if len(st.session_state.current_payment_terms) > 1:
                        if st.button("🗑️", key=f"remove_{i}", help="Rimuovi scadenza"):
                            remove_payment_term(i)
                
                # Second row for additional details
                col1, col2 = st.columns(2)
                
                with col1:
                    new_cassa = st.selectbox(
                        "Cassa",
                        CASH_ACCOUNTS,
                        index=CASH_ACCOUNTS.index(term['cassa']) if term['cassa'] in CASH_ACCOUNTS else 0,
                        key=f"cassa_{i}"
                    )
                    st.session_state.current_payment_terms[i]['cassa'] = new_cassa
                
                with col2:
                    new_note = st.text_input(
                        "Note (opzionale)",
                        value=term.get('note', ''),
                        key=f"note_{i}"
                    )
                    st.session_state.current_payment_terms[i]['note'] = new_note
                
                st.markdown("---")
    
    else:
        st.info("👆 Nessuna scadenza configurata. Usa i pulsanti sopra per aggiungere scadenze.")
    
    # Add new payment term button
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("➕ Aggiungi Scadenza", use_container_width=True):
            add_payment_term()
            st.rerun()
    
    with col2:
        if st.session_state.current_payment_terms:
            if st.button("🔄 Ricalcola Automaticamente", use_container_width=True):
                if len(st.session_state.current_payment_terms) > 0:
                    auto_split_payment(total_amount, len(st.session_state.current_payment_terms), invoice_date)
                    st.rerun()
    
    return st.session_state.current_payment_terms

def add_invoice():
    """Add a new invoice with payment terms"""
    st.subheader("➕ Aggiungi Nuova Fattura")
    
    # Check if we're in payment terms configuration mode
    if st.session_state.get('show_payment_terms_add') and st.session_state.get('temp_invoice_add'):
        invoice_data = st.session_state.temp_invoice_add
        
        st.markdown("---")
        st.markdown(f"### 📄 Configurazione Scadenze per Fattura {invoice_data['numero']}")
        st.info(f"Cliente: **{invoice_data['cliente']}** | Importo: **€ {invoice_data['importo_totale']:,.2f}**")
        
        # Payment terms manager
        payment_terms = payment_terms_manager(invoice_data['importo_totale'], invoice_data['data_documento'])
        
        # Final save button
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Salva Fattura e Scadenze", type="primary", use_container_width=True):
                if payment_terms:
                    # Validate total amount
                    total_configured = sum(term['importo'] for term in payment_terms)
                    if abs(total_configured - invoice_data['importo_totale']) >= 0.01:
                        st.error(f"⚠️ La somma delle scadenze (€ {total_configured:,.2f}) non corrisponde all'importo totale (€ {invoice_data['importo_totale']:,.2f})")
                    else:
                        # Save invoice
                        new_invoice_id = f"inv_{uuid.uuid4().hex[:8]}"
                        new_invoice = {
                            'id': new_invoice_id,
                            'numero': invoice_data['numero'],
                            'cliente': invoice_data['cliente'],
                            'divisa': invoice_data['divisa'],
                            'importo_totale': invoice_data['importo_totale'],
                            'data_documento': invoice_data['data_documento']
                        }
                        
                        # Add to invoices
                        new_invoice_df = pd.DataFrame([new_invoice])
                        st.session_state.invoices = pd.concat([st.session_state.invoices, new_invoice_df], ignore_index=True)
                        
                        # Save payment terms
                        for term in payment_terms:
                            new_term = {
                                'id': f"term_{uuid.uuid4().hex[:8]}",
                                'invoice_id': new_invoice_id,
                                'data_scadenza': term['data_scadenza'],
                                'importo': term['importo'],
                                'modalita_pagamento': term['modalita_pagamento'],
                                'cassa': term['cassa'],
                                'pagata': False
                            }
                            new_term_df = pd.DataFrame([new_term])
                            st.session_state.payment_terms = pd.concat([st.session_state.payment_terms, new_term_df], ignore_index=True)
                        
                        # Clear temporary data
                        del st.session_state.temp_invoice_add
                        del st.session_state.show_payment_terms_add
                        st.session_state.current_payment_terms = []
                        
                        st.success(f"✅ Fattura {invoice_data['numero']} salvata con {len(payment_terms)} scadenze!")
                        st.balloons()
                        st.rerun()
                else:
                    st.error("⚠️ Configura almeno una scadenza di pagamento")
        
        with col2:
            if st.button("❌ Annulla", use_container_width=True):
                # Clear temporary data
                if 'temp_invoice_add' in st.session_state:
                    del st.session_state.temp_invoice_add
                if 'show_payment_terms_add' in st.session_state:
                    del st.session_state.show_payment_terms_add
                st.session_state.current_payment_terms = []
                st.rerun()
    
    else:
        # Normal invoice form
        with st.form("add_invoice_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                numero = st.text_input("Numero *", placeholder="es. 2024-001")
                cliente = st.selectbox("Cliente *", [""] + CLIENT_OPTIONS)
                divisa = st.selectbox("Divisa *", CURRENCY_OPTIONS, index=0)
            
            with col2:
                importo_totale = st.number_input("Importo totale *", min_value=0.0, step=0.01)
                data_documento = st.date_input("Data *", value=date.today())
            
            submitted = st.form_submit_button("Continua alla configurazione scadenze", type="primary")
            
            if submitted:
                if numero and cliente and importo_totale > 0:
                    # Store invoice data temporarily
                    st.session_state.temp_invoice_add = {
                        'numero': numero,
                        'cliente': cliente,
                        'divisa': divisa,
                        'importo_totale': importo_totale,
                        'data_documento': data_documento
                    }
                    # Clear any existing payment terms
                    st.session_state.current_payment_terms = []
                    st.session_state.show_payment_terms_add = True
                    st.rerun()
                else:
                    st.error("Per favore compila tutti i campi obbligatori")

def modify_invoice():
    """Modify an existing invoice with payment terms"""
    st.subheader("✏️ Modifica Fattura")
    
    if st.session_state.invoices.empty:
        st.info("Nessuna fattura disponibile per la modifica")
        return
    
    # Check if we're in payment terms configuration mode
    if st.session_state.get('show_payment_terms_modify') and st.session_state.get('temp_invoice_modify'):
        invoice_data = st.session_state.temp_invoice_modify
        selected_index = st.session_state.get('modify_invoice_index')
        
        st.markdown("---")
        st.markdown(f"### 📄 Modifica Scadenze per Fattura {invoice_data['numero']}")
        st.info(f"Cliente: **{invoice_data['cliente']}** | Importo: **€ {invoice_data['importo_totale']:,.2f}**")
        
        # Load existing payment terms for this invoice
        if 'current_payment_terms' not in st.session_state or not st.session_state.current_payment_terms:
            invoice_id = st.session_state.invoices.iloc[selected_index]['id']
            existing_terms = st.session_state.payment_terms[
                st.session_state.payment_terms['invoice_id'] == invoice_id
            ]
            
            if not existing_terms.empty:
                st.session_state.current_payment_terms = []
                for _, term in existing_terms.iterrows():
                    st.session_state.current_payment_terms.append({
                        'id': len(st.session_state.current_payment_terms),
                        'data_scadenza': term['data_scadenza'],
                        'importo': term['importo'],
                        'modalita_pagamento': term['modalita_pagamento'],
                        'cassa': term['cassa'],
                        'note': term.get('note', '')
                    })
        
        # Payment terms manager
        payment_terms = payment_terms_manager(invoice_data['importo_totale'], invoice_data['data_documento'])
        
        # Final save button
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Aggiorna Fattura e Scadenze", type="primary", use_container_width=True):
                if payment_terms:
                    # Validate total amount
                    total_configured = sum(term['importo'] for term in payment_terms)
                    if abs(total_configured - invoice_data['importo_totale']) >= 0.01:
                        st.error(f"⚠️ La somma delle scadenze (€ {total_configured:,.2f}) non corrisponde all'importo totale (€ {invoice_data['importo_totale']:,.2f})")
                    else:
                        # Update invoice
                        invoice_id = st.session_state.invoices.iloc[selected_index]['id']
                        
                        st.session_state.invoices.loc[selected_index, 'numero'] = invoice_data['numero']
                        st.session_state.invoices.loc[selected_index, 'cliente'] = invoice_data['cliente']
                        st.session_state.invoices.loc[selected_index, 'divisa'] = invoice_data['divisa']
                        st.session_state.invoices.loc[selected_index, 'importo_totale'] = invoice_data['importo_totale']
                        st.session_state.invoices.loc[selected_index, 'data_documento'] = invoice_data['data_documento']
                        
                        # Delete existing payment terms for this invoice
                        st.session_state.payment_terms = st.session_state.payment_terms[
                            st.session_state.payment_terms['invoice_id'] != invoice_id
                        ]
                        
                        # Save new payment terms
                        for term in payment_terms:
                            new_term = {
                                'id': f"term_{uuid.uuid4().hex[:8]}",
                                'invoice_id': invoice_id,
                                'data_scadenza': term['data_scadenza'],
                                'importo': term['importo'],
                                'modalita_pagamento': term['modalita_pagamento'],
                                'cassa': term['cassa'],
                                'pagata': False
                            }
                            new_term_df = pd.DataFrame([new_term])
                            st.session_state.payment_terms = pd.concat([st.session_state.payment_terms, new_term_df], ignore_index=True)
                        
                        # Clear temporary data
                        del st.session_state.temp_invoice_modify
                        del st.session_state.show_payment_terms_modify
                        del st.session_state.modify_invoice_index
                        st.session_state.current_payment_terms = []
                        
                        st.success(f"✅ Fattura {invoice_data['numero']} aggiornata con {len(payment_terms)} scadenze!")
                        st.rerun()
                else:
                    st.error("⚠️ Configura almeno una scadenza di pagamento")
        
        with col2:
            if st.button("❌ Annulla", use_container_width=True):
                # Clear temporary data
                if 'temp_invoice_modify' in st.session_state:
                    del st.session_state.temp_invoice_modify
                if 'show_payment_terms_modify' in st.session_state:
                    del st.session_state.show_payment_terms_modify
                if 'modify_invoice_index' in st.session_state:
                    del st.session_state.modify_invoice_index
                st.session_state.current_payment_terms = []
                st.rerun()
    
    else:
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
                
                submitted = st.form_submit_button("Continua alla modifica scadenze", type="primary")
                
                if submitted:
                    if numero and cliente and importo_totale > 0:
                        # Store invoice data temporarily
                        st.session_state.temp_invoice_modify = {
                            'numero': numero,
                            'cliente': cliente,
                            'divisa': divisa,
                            'importo_totale': importo_totale,
                            'data_documento': data_documento
                        }
                        st.session_state.modify_invoice_index = selected_index
                        # Clear any existing payment terms
                        st.session_state.current_payment_terms = []
                        st.session_state.show_payment_terms_modify = True
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
            invoice_id = invoice_data['id']
            
            # Delete invoice
            st.session_state.invoices = st.session_state.invoices.drop(selected_index).reset_index(drop=True)
            
            # Delete related payment terms
            st.session_state.payment_terms = st.session_state.payment_terms[
                st.session_state.payment_terms['invoice_id'] != invoice_id
            ]
            
            st.success(f"Fattura {invoice_data['numero']} eliminata con successo!")
            st.rerun()

# Main App
def main():
    # st.session_state

    st.set_page_config(page_title="Sistema Gestione Fatture", page_icon="📄", layout="wide")
    
    # st.write("---")
     
    # Action menu below the table
    # st.subheader("🛠️ Operazioni")
    
    # Horizontal menu with columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ Aggiungi Fattura", use_container_width=True):
            st.session_state.show_section = "add"
    
    # with col2:
    #     if st.button("✏️ Modifica Fattura", use_container_width=True):
    #         st.session_state.show_section = "modify"
    
    # with col3:
    #     if st.button("🗑️ Elimina Fattura", use_container_width=True):
    #         st.session_state.show_section = "delete"
    
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
    
if __name__ == "__main__":
    main()