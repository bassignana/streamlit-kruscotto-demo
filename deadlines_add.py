import streamlit as st
from decimal import Decimal, getcontext, ROUND_HALF_UP
from datetime import date, datetime, timedelta
from typing import List, Dict, Tuple

getcontext().prec = 2

# Constants
PAYMENT_METHODS = ['Bonifico', 'Contanti', 'Assegno', 'Carta di credito', 'RID', 'Altro']
CASH_ACCOUNTS = ['Banca Intesa', 'Cassa Contanti', 'Cassa Generica', 'INTESA SAN PAOLO']

def decimal_round(value: float, places: int = 2) -> Decimal:
    """Safely round a decimal value for financial calculations"""
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def validate_payment_terms(terms: List[Dict], total_amount: float) -> Tuple[bool, List[str]]:
    """Validate payment terms against total amount"""
    errors = []

    if not terms:
        errors.append("Almeno una scadenza di pagamento è richiesta")
        return False, errors

    total_configured = sum(Decimal(str(term.get('amount', 0))) for term in terms)
    total_decimal = Decimal(str(total_amount))

    if abs(total_configured - total_decimal) > Decimal('0.01'):
        errors.append(f"La somma delle scadenze (€ {total_configured:.2f}) non corrisponde all'importo totale (€ {total_decimal:.2f})")

    for i, term in enumerate(terms):
        if not term.get('due_date'):
            errors.append(f"Data scadenza mancante per la scadenza {i+1}")

        if term.get('amount', 0) <= 0:
            errors.append(f"Importo deve essere maggiore di zero per la scadenza {i+1}")

        if not term.get('payment_method'):
            errors.append(f"Modalità di pagamento mancante per la scadenza {i+1}")

        if not term.get('cash_account'):
            errors.append(f"Cassa mancante per la scadenza {i+1}")

    return len(errors) == 0, errors

def auto_split_payment(total_amount: float, num_installments: int, start_date: date, interval_days: int = 30) -> List[Dict]:
    """Automatically split payment into equal installments"""
    if num_installments <= 0:
        return []

    total_decimal = Decimal(str(total_amount))
    amount_per_installment = total_decimal / num_installments

    terms = []
    total_allocated = Decimal('0')

    for i in range(num_installments):
        # Calculate amount for this installment
        if i == num_installments - 1:
            # Last installment gets the remainder to avoid rounding errors
            installment_amount = total_decimal - total_allocated
        else:
            installment_amount = decimal_round(float(amount_per_installment))
            total_allocated += installment_amount

        term = {
            'due_date': start_date + timedelta(days=interval_days * (i + 1)),
            'amount': float(installment_amount),
            'payment_method': 'Bonifico',
            'cash_account': 'Banca Intesa',
            'notes': f'Rata {i + 1} di {num_installments}'
        }
        terms.append(term)

    return terms

def check_existing_payment_terms(supabase_client, user_id: str, invoice_id: str) -> bool:
    """Check if payment terms already exist for an invoice"""
    try:
        result = supabase_client.table('payment_terms').select('id').eq('user_id', user_id).eq('invoice_id', invoice_id).limit(1).execute()
        return len(result.data) > 0
    except Exception as e:
        st.error(f"Errore nel controllo delle scadenze esistenti: {str(e)}")
        return False

def save_payment_terms_to_db(supabase_client, user_id: str, invoice_id: str, terms: List[Dict]) -> bool:
    """Save payment terms to database"""
    try:
        # Insert new payment terms
        for term in terms:
            payment_term_data = {
                'user_id': user_id,
                'invoice_id': invoice_id,
                'due_date': term['due_date'].isoformat(),
                'amount': float(decimal_round(term['amount'])),
                'payment_method': term['payment_method'],
                'cash_account': term['cash_account'],
                'notes': term.get('notes', ''),
                'is_paid': False
            }

            supabase_client.table('payment_terms').insert(payment_term_data).execute()

        return True

    except Exception as e:
        st.error(f"Errore nel salvataggio delle scadenze: {str(e)}")
        return False

def render_payment_terms_form(supabase_client, user_id: str, invoice_data: Dict) -> None:
    """Render the payment terms configuration form"""

    # Initialize session state for payment terms
    if 'current_payment_terms' not in st.session_state:
        st.session_state.current_payment_terms = []

    # st.subheader("💰 Configurazione Scadenze di Pagamento")
    #
    # # Display invoice info
    # col1, col2, col3 = st.columns(3)
    # with col1:
    #     st.metric("📄 Fattura", invoice_data['invoice_number'])
    # with col2:
    #     st.metric("💰 Importo Totale", f"€ {invoice_data['total_amount']:,.2f}")
    # with col3:
    #     st.metric("📅 Data", invoice_data['document_date'].strftime('%d/%m/%Y'))
    #
    # st.markdown("---")

    # Quick setup options
    with st.expander("⚡ Configurazione Rapida", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Pagamento Unico", use_container_width=True):
                st.session_state.current_payment_terms = [{
                    'due_date': invoice_data['document_date'] + timedelta(days=30),
                    'amount': invoice_data['total_amount'],
                    'payment_method': 'Bonifico',
                    'cash_account': 'Banca Intesa',
                    'notes': 'Pagamento unico'
                }]
                st.rerun()

        with col2:
            if st.button("2 Rate Mensili", use_container_width=True):
                st.session_state.current_payment_terms = auto_split_payment(
                    invoice_data['total_amount'], 2, invoice_data['document_date'], 30
                )
                st.rerun()

        with col3:
            if st.button("3 Rate Mensili", use_container_width=True):
                st.session_state.current_payment_terms = auto_split_payment(
                    invoice_data['total_amount'], 3, invoice_data['document_date'], 30
                )
                st.rerun()

        # Custom split
        # st.markdown("**Configurazione Personalizzata:**")
        split_col1, split_col2, split_col3 = st.columns([2, 2, 1])

        with split_col1:
            num_installments = st.number_input("Numero rate", min_value=1, max_value=12, value=1)

        with split_col2:
            interval_days = st.number_input("Giorni tra rate", min_value=1, max_value=365, value=30)

        with split_col3:
            if st.button("Applica Configurazione", use_container_width=True):
                st.session_state.current_payment_terms = auto_split_payment(
                    invoice_data['total_amount'], num_installments, invoice_data['document_date'], interval_days
                )
                st.rerun()

    # Current payment terms configuration
    if st.session_state.current_payment_terms:
        st.markdown("###   ")

        # Summary
        total_configured = sum(term['amount'] for term in st.session_state.current_payment_terms)
        remaining = invoice_data['total_amount'] - total_configured

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Importo Totale", f"€ {invoice_data['total_amount']:,.2f}")
        with col2:
            st.metric("Importo Configurato", f"€ {total_configured:,.2f}")
        with col3:
            st.metric("Rimanente", f"€ {remaining:,.2f}")
            if abs(remaining) >= 0.01:
                st.warning(f"⚠️ Differenza di € {remaining:,.2f}")

        # Payment terms list
        for i, term in enumerate(st.session_state.current_payment_terms):
            with st.container():
                st.markdown(f"##### Scadenza {i + 1}")

                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

                with col1:
                    new_date = st.date_input(
                        "Data Scadenza",
                        value=term['due_date'],
                        key=f"date_{i}"
                    )
                    st.session_state.current_payment_terms[i]['due_date'] = new_date

                with col2:
                    new_amount = st.number_input(
                        "Importo (€)",
                        min_value=0.0,
                        value=max(0.0, float(term['amount'])),
                        step=0.01,
                        key=f"amount_{i}"
                    )
                    st.session_state.current_payment_terms[i]['amount'] = new_amount

                with col3:
                    new_payment_method = st.selectbox(
                        "Modalità",
                        PAYMENT_METHODS,
                        index=PAYMENT_METHODS.index(term['payment_method']) if term['payment_method'] in PAYMENT_METHODS else 0,
                        key=f"method_{i}"
                    )
                    st.session_state.current_payment_terms[i]['payment_method'] = new_payment_method

                with col4:
                    st.write("")  # Spacing
                    st.write("")  # Spacing
                    if len(st.session_state.current_payment_terms) > 1:
                        if st.button("🗑️", key=f"remove_{i}", help="Rimuovi scadenza"):
                            st.session_state.current_payment_terms.pop(i)
                            st.rerun()

                # Second row for additional details
                col1, col2 = st.columns(2)

                with col1:
                    new_cash_account = st.selectbox(
                        "Cassa",
                        CASH_ACCOUNTS,
                        index=CASH_ACCOUNTS.index(term['cash_account']) if term['cash_account'] in CASH_ACCOUNTS else 0,
                        key=f"cash_{i}"
                    )
                    st.session_state.current_payment_terms[i]['cash_account'] = new_cash_account

                with col2:
                    new_notes = st.text_input(
                        "Note (opzionale)",
                        value=term.get('notes', ''),
                        key=f"notes_{i}"
                    )
                    st.session_state.current_payment_terms[i]['notes'] = new_notes

                st.markdown("---")

    else:
        # st.info("👆 Nessuna scadenza configurata. Usa i pulsanti sopra per aggiungere scadenze.")
        pass
    # Add new payment term button
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Aggiungi Scadenza", use_container_width=False):
            new_term = {
                'due_date': invoice_data['document_date'] + timedelta(days=30),
                'amount': 0.0,
                'payment_method': 'Bonifico',
                'cash_account': 'Banca Intesa',
                'notes': ''
            }
            st.session_state.current_payment_terms.append(new_term)
            st.rerun()

    with col2:
        if st.session_state.current_payment_terms:
            if st.button("Dividi Importo tra scadenze", use_container_width=False):
                if len(st.session_state.current_payment_terms) > 0:
                    st.session_state.current_payment_terms = auto_split_payment(
                        invoice_data['total_amount'],
                        len(st.session_state.current_payment_terms),
                        invoice_data['document_date']
                    )
                    st.rerun()

    # Save buttons
    if st.session_state.current_payment_terms:
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("💾 Salva Scadenze", type="primary", use_container_width=True):
                is_valid, errors = validate_payment_terms(st.session_state.current_payment_terms, invoice_data['total_amount'])

                if not is_valid:
                    for error in errors:
                        st.error(error)
                else:
                    if save_payment_terms_to_db(supabase_client, user_id, invoice_data['id'], st.session_state.current_payment_terms):
                        st.success(f"✅ Scadenze salvate con successo!")
                        st.session_state.current_payment_terms = []
                        
                        st.rerun()

        with col2:
            if st.button("❌ Annulla", use_container_width=True):
                st.session_state.current_payment_terms = []
                st.rerun()

def main():
    """Main function for adding payment terms"""

    st.set_page_config(
        page_title="Aggiungi Scadenze Pagamento",
        page_icon="💰",
        layout="wide"
    )

    # Set precision for financial calculations
    getcontext().prec = 28

    # Check authentication
    if 'user' not in st.session_state or not st.session_state.user:
        st.error("🔐 Effettuare il login per accedere a questa pagina")
        st.stop()

    user_id = st.session_state.user.id

    if 'client' not in st.session_state:
        st.error("❌ Errore di connessione al database")
        st.stop()

    supabase_client = st.session_state.client

    st.subheader("Aggiungi Scadenze di Pagamento")

    # Load invoices for selection
    try:
        # Load both invoice types
        emesse_invoices_result = supabase_client.table('fatture_emesse').select('*').eq('user_id', user_id).order('document_date', desc=True).execute()
        ricevute_invoices_result = supabase_client.table('fatture_ricevute').select('*').eq('user_id', user_id).order('document_date', desc=True).execute()

        # Combine both invoice types into a single list with type identifier
        all_invoice_options = []
        all_invoice_data = []

        # Add emesse invoices
        if emesse_invoices_result.data:
            for inv in emesse_invoices_result.data:
                option_text = f"📤 EMESSA: {inv['invoice_number']} - € {inv['total_amount']:,.2f} ({inv['document_date']})"
                all_invoice_options.append(option_text)
                inv['invoice_type'] = 'emesse'  # Add type identifier
                all_invoice_data.append(inv)

        # Add ricevute invoices
        if ricevute_invoices_result.data:
            for inv in ricevute_invoices_result.data:
                option_text = f"📥 RICEVUTA: {inv['invoice_number']} - € {inv['total_amount']:,.2f} ({inv['document_date']})"
                all_invoice_options.append(option_text)
                inv['invoice_type'] = 'ricevute'  # Add type identifier
                all_invoice_data.append(inv)

        # Check if we have any invoices at all
        if not all_invoice_options:
            st.warning("⚠️ Nessuna fattura trovata. Creare una fattura prima di gestire le scadenze.")
            return

        # Single selectbox for all invoices
        selected_invoice = st.selectbox("Seleziona Fattura:", [""] + all_invoice_options)

        if selected_invoice:  # Only proceed if something is selected
            selected_index = all_invoice_options.index(selected_invoice)
            invoice_data = all_invoice_data[selected_index]

            # Convert date string to date object
            invoice_data['document_date'] = datetime.strptime(invoice_data['document_date'], '%Y-%m-%d').date()

            # Check if payment terms already exist for this invoice
            if check_existing_payment_terms(supabase_client, user_id, invoice_data['id']):
                st.warning("Questa fattura ha già delle scadenze di pagamento configurate. \n Usare le pagine nel menu Scadenze, a sinistra, per riconfigurare.")
                #
                # col1, col2, col3 = st.columns([1, 1, 1])
                #
                # with col1:
                #     st.info("**Per modificare le scadenze esistenti:**")
                #     if st.button("🔧 Vai alla Pagina di Modifica", type="primary", use_container_width=True):
                #         st.info("🔄 Reindirizzamento alla pagina di modifica...")
                #         st.markdown("**Nota:** Implementare la navigazione alla pagina `page_emesse_deadlines_modify_terms.py`")
                #
                # with col2:
                #     st.info("**Per sostituire tutte le scadenze:**")
                #     if st.button("🔄 Riconfigura Scadenze", type="secondary", use_container_width=True):
                #         if 'confirm_replace' not in st.session_state:
                #             st.session_state.confirm_replace = False
                #
                #         if not st.session_state.confirm_replace:
                #             if st.button("⚠️ Conferma Sostituzione", key="confirm_replace_btn"):
                #                 st.session_state.confirm_replace = True
                #                 st.rerun()
                #         else:
                #             try:
                #                 supabase_client.table('payment_terms').delete().eq('user_id', user_id).eq('invoice_id', invoice_data['id']).execute()
                #                 st.session_state.confirm_replace = False
                #                 st.success("✅ Scadenze esistenti eliminate. Ora puoi configurare nuove scadenze.")
                #                 st.rerun()
                #             except Exception as e:
                #                 st.error(f"Errore nell'eliminazione: {str(e)}")
                #
                # with col3:
                #     st.info("**Per vedere le scadenze attuali:**")
                #     if st.button("👁️ Visualizza Scadenze", use_container_width=True):
                #         st.info("🔄 Reindirizzamento alla pagina di visualizzazione...")
                #         st.markdown("**Nota:** Implementare la navigazione alla pagina di visualizzazione")

                return

            # Show invoice type info
            invoice_type_emoji = "📤" if invoice_data['invoice_type'] == 'emesse' else "📥"
            invoice_type_text = "Fattura Emessa" if invoice_data['invoice_type'] == 'emesse' else "Fattura Ricevuta"
            # st.info(f"{invoice_type_emoji} Stai configurando scadenze per una **{invoice_type_text}**")

            # Show the payment terms form
            render_payment_terms_form(supabase_client, user_id, invoice_data)
    except Exception as e:
        st.error(f"Errore nel caricamento delle fatture: {str(e)}")

if __name__ == "__main__":
    main()