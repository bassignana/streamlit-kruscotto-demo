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

def view_all_invoices():
    """Display all invoices with embedded search and payment terms"""
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
        # col1, col2, col3, col4 = st.columns(4)

        # with col1:
        #     total_invoices = len(filtered_df)
        #     st.metric("Fatture Mostrate", f"{total_invoices}/{len(st.session_state.invoices)}")
        # with col2:
        #     if not filtered_df.empty:
        #         total_amount = filtered_df['importo_totale'].sum()
        #         st.metric("Importo Totale", f"€ {total_amount:,.2f}")
        #     else:
        #         st.metric("Importo Totale", "€ 0,00")
        # with col3:
        #     if not filtered_df.empty:
        #         unique_clients_filtered = filtered_df['cliente'].nunique()
        #         st.metric("Clienti Unici", unique_clients_filtered)
        #     else:
        #         st.metric("Clienti Unici", "0")
        # with col4:
        #     if not filtered_df.empty:
        #         avg_amount = filtered_df['importo_totale'].mean()
        #         st.metric("Importo Medio", f"€ {avg_amount:,.2f}")
        #     else:
        #         st.metric("Importo Medio", "€ 0,00")
        
        # st.write("---")
        
        # Display filtered results with payment terms
        if filtered_df.empty:
            st.warning("Nessuna fattura corrisponde ai criteri di ricerca selezionati")
        else:
            # Display invoices with expandable payment terms
            for _, invoice in filtered_df.iterrows():
                with st.expander(f"📄 {invoice['numero']} - {invoice['cliente']} (€ {invoice['importo_totale']:,.2f})", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Data:** {invoice['data_documento']}")
                        st.write(f"**Cliente:** {invoice['cliente']}")
                        st.write(f"**Divisa:** {invoice['divisa']}")
                    
                    with col2:
                        st.write(f"**Importo Totale:** € {invoice['importo_totale']:,.2f}")
                    
                    # Show payment terms
                    invoice_terms = st.session_state.payment_terms[
                        st.session_state.payment_terms['invoice_id'] == invoice['id']
                    ]
                    
                    if not invoice_terms.empty:
                        st.markdown("#### 💰 Scadenze:")
                        
                        # Create a display dataframe
                        terms_display = invoice_terms.copy()
                        terms_display['Stato'] = terms_display['pagata'].apply(lambda x: '✅ Pagata' if x else '⏳ In attesa')
                        terms_display = terms_display[['data_scadenza', 'importo', 'modalita_pagamento', 'cassa', 'Stato']]
                        terms_display.columns = ['Data Scadenza', 'Importo €', 'Modalità', 'Cassa', 'Stato']
                        
                        st.dataframe(terms_display, use_container_width=True)
                        
                        # Payment summary
                        total_terms = len(invoice_terms)
                        paid_terms = len(invoice_terms[invoice_terms['pagata'] == True])
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Scadenze Totali", total_terms)
                        with col2:
                            st.metric("Scadenze Pagate", paid_terms)
                        with col3:
                            st.metric("Scadenze in Attesa", total_terms - paid_terms)
                    else:
                        st.warning("⚠️ Nessuna scadenza configurata per questa fattura")
            
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


# Main App
def main():
    st.session_state

    st.set_page_config(page_title="Sistema Gestione Fatture", page_icon="📄", layout="wide")
    
    st.title("📄 Sistema Gestione Fatture")
    uploaded_files = xml_invoice_uploader()

    tab1, tab2, tab3, tab4 = st.tabs([
        "💰 Fatture di Vendita", 
        "🛒 Fatture di Acquisto", 
        "📊 Riepilogo Finanziario",
        "uploader"
    ])

    with tab1:
        # st.write("Gestisci le tue fatture: aggiungi, modifica, elimina e cerca facilmente")
        
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
        # if st.session_state.show_section is None:
        #     st.write("---")
        #     st.info("💡 **Suggerimento:** Usa la ricerca per trovare rapidamente le fatture di un cliente specifico")

    with tab2:
        st.write("📝 Fatture di Acquisto - Coming Soon")
        st.info("Questa sezione sarà disponibile presto per gestire le fatture dei fornitori")

    with tab3:
        view_financial_summary()

    with tab4:
        invoice_xml_processor.invoice_xml_processor_page()

if __name__ == "__main__":
    main()