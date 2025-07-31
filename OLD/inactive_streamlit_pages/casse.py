import streamlit as st
import pandas as pd
import uuid

# Initialize session state for cash accounts (casse)
if 'cash_accounts' not in st.session_state:
    st.session_state.cash_accounts = pd.DataFrame({
        'id': ['cash_001', 'cash_002', 'cash_003', 'cash_004', 'cash_005'],
        'nome': ['Cassa Contanti', 'Cassa Generica', 'Pagamento da definire', 'Banca intesa', 'INTESA SAN PAOLO'],
        'iban': ['', '', '', 'IT15X0301503200000004223581', 'IT71L0306904057100000000564'],
        'predefinito': [False, False, False, False, False]
    })

def add_cash_account():
    """Add a new cash account"""
    st.subheader("➕ Aggiungi Nuova Cassa")
    
    with st.form("add_cash_account_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            nome = st.text_input("Nome *", placeholder="es. Cassa Principale")
            iban = st.text_input("IBAN", placeholder="es. IT60X0542811101000000123456")
        
        with col2:
            predefinito = st.checkbox("Cassa Predefinita")
        
        submitted = st.form_submit_button("Aggiungi Cassa", type="primary")
        
        if submitted:
            if nome:
                new_account = {
                    'id': f"cash_{uuid.uuid4().hex[:8]}",
                    'nome': nome,
                    'iban': iban,
                    'predefinito': predefinito
                }
                
                # If this is set as default, unset all others
                if predefinito:
                    st.session_state.cash_accounts['predefinito'] = False
                
                new_row = pd.DataFrame([new_account])
                st.session_state.cash_accounts = pd.concat([st.session_state.cash_accounts, new_row], ignore_index=True)
                
                st.success(f"Cassa {nome} aggiunta con successo!")
                st.rerun()
            else:
                st.error("Per favore inserisci almeno il nome della cassa")

def modify_cash_account():
    """Modify an existing cash account"""
    st.subheader("✏️ Modifica Cassa")
    
    if st.session_state.cash_accounts.empty:
        st.info("Nessuna cassa disponibile per la modifica")
        return
    
    account_options = st.session_state.cash_accounts.apply(
        lambda row: f"{row['nome']} - {row['iban'] if row['iban'] else 'Nessun IBAN'}", axis=1
    ).tolist()
    
    selected_account = st.selectbox("Seleziona cassa da modificare:", [""] + account_options)
    
    if selected_account:
        selected_index = account_options.index(selected_account)
        account_data = st.session_state.cash_accounts.iloc[selected_index]
        
        with st.form("modify_cash_account_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("Nome *", value=account_data['nome'])
                iban = st.text_input("IBAN", value=account_data['iban'] if pd.notna(account_data['iban']) else "")
            
            with col2:
                predefinito = st.checkbox("Cassa Predefinita", value=bool(account_data['predefinito']))
            
            submitted = st.form_submit_button("Aggiorna Cassa", type="primary")
            
            if submitted:
                if nome:
                    # If this is set as default, unset all others
                    if predefinito:
                        st.session_state.cash_accounts['predefinito'] = False
                    
                    st.session_state.cash_accounts.loc[selected_index, 'nome'] = nome
                    st.session_state.cash_accounts.loc[selected_index, 'iban'] = iban
                    st.session_state.cash_accounts.loc[selected_index, 'predefinito'] = predefinito
                    
                    st.success(f"Cassa {nome} aggiornata con successo!")
                    st.rerun()
                else:
                    st.error("Per favore inserisci il nome della cassa")

def delete_cash_account():
    """Delete a cash account"""
    st.subheader("🗑️ Elimina Cassa")
    
    if st.session_state.cash_accounts.empty:
        st.info("Nessuna cassa disponibile per l'eliminazione")
        return
    
    account_options = st.session_state.cash_accounts.apply(
        lambda row: f"{row['nome']} - {row['iban'] if row['iban'] else 'Nessun IBAN'}", axis=1
    ).tolist()
    
    selected_account = st.selectbox("Seleziona cassa da eliminare:", [""] + account_options)
    
    if selected_account:
        selected_index = account_options.index(selected_account)
        account_data = st.session_state.cash_accounts.iloc[selected_index]
        
        st.write("**Dettagli cassa da eliminare:**")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Nome:** {account_data['nome']}")
            st.write(f"**IBAN:** {account_data['iban'] if account_data['iban'] else 'Non specificato'}")
        with col2:
            predefinito_text = "Sì" if account_data['predefinito'] else "No"
            st.write(f"**Predefinito:** {predefinito_text}")
        
        st.warning("⚠️ Questa azione non può essere annullata!")
        
        if st.button("Elimina Cassa", type="secondary"):
            st.session_state.cash_accounts = st.session_state.cash_accounts.drop(selected_index).reset_index(drop=True)
            st.success(f"Cassa {account_data['nome']} eliminata con successo!")
            st.rerun()

def view_cash_accounts():
    """Display all cash accounts with embedded search"""
    st.subheader("🏦 Casse")
    
    if st.session_state.cash_accounts.empty:
        st.info("Nessuna cassa presente nel sistema")
    else:
        # Search filter above the table
        search_term = st.text_input(
            "🔎 Cerca...",
            placeholder="Cerca per nome o IBAN...",
            help="Cerca in tutti i campi"
        )
        
        # Apply search filter
        filtered_df = st.session_state.cash_accounts.copy()
        
        if search_term:
            mask = (
                filtered_df['nome'].astype(str).str.contains(search_term, case=False, na=False) |
                filtered_df['iban'].astype(str).str.contains(search_term, case=False, na=False)
            )
            filtered_df = filtered_df[mask]
        
        # Display summary statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            total_accounts = len(filtered_df)
            st.metric("Casse Mostrate", f"{total_accounts}/{len(st.session_state.cash_accounts)}")
        with col2:
            accounts_with_iban = len(filtered_df[filtered_df['iban'] != ''])
            st.metric("Con IBAN", accounts_with_iban)
        with col3:
            default_accounts = len(filtered_df[filtered_df['predefinito'] == True])
            st.metric("Predefinite", default_accounts)
        
        st.write("---")
        
        # Display filtered results
        if filtered_df.empty:
            st.warning("Nessuna cassa corrisponde ai criteri di ricerca")
        else:
            # Prepare display dataframe
            display_df = filtered_df.copy()
            display_df = display_df.drop('id', axis=1)
            
            # Format predefinito column
            display_df['predefinito'] = display_df['predefinito'].apply(
                lambda x: "🔴 Sì" if x else "⚪ No"
            )
            
            # Rename columns for display
            display_df.columns = ['Nome', 'IBAN', 'Predefinito']
            
            st.dataframe(display_df, use_container_width=True)
            
            if search_term:
                st.caption(f"📊 Mostrando {len(filtered_df)} di {len(st.session_state.cash_accounts)} casse totali")

def cash_account_operations():
    """Handle cash account operations"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ Aggiungi Cassa", use_container_width=True):
            st.session_state.show_cash_section = "add"
    
    with col2:
        if st.button("✏️ Modifica Cassa", use_container_width=True):
            st.session_state.show_cash_section = "modify"
    
    with col3:
        if st.button("🗑️ Elimina Cassa", use_container_width=True):
            st.session_state.show_cash_section = "delete"
    
    # Initialize session state
    if 'show_cash_section' not in st.session_state:
        st.session_state.show_cash_section = None
    
    # Show selected section
    if st.session_state.show_cash_section == "add":
        st.write("---")
        add_cash_account()
        if st.button("❌ Chiudi", key="close_cash_add"):
            st.session_state.show_cash_section = None
            st.rerun()
    
    elif st.session_state.show_cash_section == "modify":
        st.write("---")
        modify_cash_account()
        if st.button("❌ Chiudi", key="close_cash_modify"):
            st.session_state.show_cash_section = None
            st.rerun()
    
    elif st.session_state.show_cash_section == "delete":
        st.write("---")
        delete_cash_account()
        if st.button("❌ Chiudi", key="close_cash_delete"):
            st.session_state.show_cash_section = None
            st.rerun()

# Main App
def main():
    st.set_page_config(page_title="Gestione Casse", page_icon="🏦", layout="wide")
    
    st.title("🏦 Gestione Casse")
    st.write("Gestisci i tuoi conti e metodi di pagamento")
    
    # Always show cash accounts table
    view_cash_accounts()
    
    st.write("---")
    
    # Cash account operations
    st.subheader("🛠️ Operazioni")
    cash_account_operations()
    
    # Footer
    if st.session_state.get('show_cash_section') is None:
        st.write("---")
        st.info("💡 **Suggerimento:** Usa la ricerca per trovare rapidamente una cassa specifica")

if __name__ == "__main__":
    main()