import streamlit as st
import pandas as pd
from decimal import Decimal, getcontext, ROUND_HALF_UP
from datetime import date, datetime, timedelta
from typing import List, Dict, Tuple
import time

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

def load_payment_terms_from_db(supabase_client, user_id: str, invoice_id: str) -> List[Dict]:
    """Load payment terms from database for a specific invoice"""
    try:
        result = supabase_client.table('payment_terms').select('*').eq('user_id', user_id).eq('invoice_id', invoice_id).order('due_date').execute()

        terms = []
        for row in result.data:
            terms.append({
                'id': row['id'],
                'due_date': datetime.strptime(row['due_date'], '%Y-%m-%d').date(),
                'amount': float(row['amount']),
                'payment_method': row['payment_method'],
                'cash_account': row['cash_account'],
                'notes': row.get('notes', ''),
                'is_paid': row.get('is_paid', False),
                'payment_date': datetime.strptime(row['payment_date'], '%Y-%m-%d').date() if row.get('payment_date') else None
            })

        return terms

    except Exception as e:
        st.error(f"Errore nel caricamento delle scadenze: {str(e)}")
        return []

def save_payment_terms_to_db(supabase_client, user_id: str, invoice_id: str, terms: List[Dict]) -> bool:
    """Save payment terms to database (replacing existing ones)"""
    try:
        # First, delete existing payment terms for this invoice
        supabase_client.table('payment_terms').delete().eq('user_id', user_id).eq('invoice_id', invoice_id).execute()

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
                'is_paid': term.get('is_paid', False)
            }

            if term.get('payment_date'):
                payment_term_data['payment_date'] = term['payment_date'].isoformat()

            supabase_client.table('payment_terms').insert(payment_term_data).execute()

        return True

    except Exception as e:
        st.error(f"Errore nel salvataggio delle scadenze: {str(e)}")
        return False

def update_payment_status(supabase_client, user_id: str, payment_term_id: str, is_paid: bool, payment_date: date = None) -> bool:
    """Update payment status for a specific payment term"""
    try:
        update_data = {
            'is_paid': is_paid,
            'updated_at': datetime.now().isoformat()
        }

        if is_paid and payment_date:
            update_data['payment_date'] = payment_date.isoformat()
        elif not is_paid:
            update_data['payment_date'] = None

        supabase_client.table('payment_terms').update(update_data).eq('id', payment_term_id).eq('user_id', user_id).execute()
        return True

    except Exception as e:
        st.error(f"Errore nell'aggiornamento dello stato di pagamento: {str(e)}")
        return False

def get_invoice_payment_summary(supabase_client, user_id: str, invoice_id: str) -> Dict:
    """Get payment summary for an invoice"""
    try:
        result = supabase_client.table('payment_terms').select('*').eq('user_id', user_id).eq('invoice_id', invoice_id).execute()

        if not result.data:
            return {
                'total_terms': 0,
                'paid_terms': 0,
                'pending_terms': 0,
                'total_amount': 0,
                'paid_amount': 0,
                'pending_amount': 0,
                'overdue_terms': 0,
                'overdue_amount': 0
            }

        total_terms = len(result.data)
        paid_terms = sum(1 for term in result.data if term['is_paid'])
        pending_terms = total_terms - paid_terms

        total_amount = sum(Decimal(str(term['amount'])) for term in result.data)
        paid_amount = sum(Decimal(str(term['amount'])) for term in result.data if term['is_paid'])
        pending_amount = total_amount - paid_amount

        # Calculate overdue
        today = date.today()
        overdue_terms = 0
        overdue_amount = Decimal('0')

        for term in result.data:
            if not term['is_paid']:
                due_date = datetime.strptime(term['due_date'], '%Y-%m-%d').date()
                if due_date < today:
                    overdue_terms += 1
                    overdue_amount += Decimal(str(term['amount']))

        return {
            'total_terms': total_terms,
            'paid_terms': paid_terms,
            'pending_terms': pending_terms,
            'total_amount': float(total_amount),
            'paid_amount': float(paid_amount),
            'pending_amount': float(pending_amount),
            'overdue_terms': overdue_terms,
            'overdue_amount': float(overdue_amount)
        }

    except Exception as e:
        st.error(f"Errore nel calcolo del riepilogo pagamenti: {str(e)}")
        return {}

def render_payment_terms_modification_form(supabase_client, user_id: str, invoice_data: Dict, existing_terms: List[Dict]) -> None:
    """Render the payment terms modification form"""

    # Load existing terms into session state if not already there
    if 'current_payment_terms' not in st.session_state or not st.session_state.current_payment_terms:
        st.session_state.current_payment_terms = [
            {
                'due_date': term['due_date'],
                'amount': term['amount'],
                'payment_method': term['payment_method'],
                'cash_account': term['cash_account'],
                'notes': term.get('notes', ''),
                'is_paid': term.get('is_paid', False),
                'payment_date': term.get('payment_date')
            }
            for term in existing_terms
        ]

    # st.subheader("✏️ Modifica Scadenze di Pagamento")
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

    # Quick reconfiguration options


    # Current payment terms modification
    # st.markdown("### Modifica Scadenze Esistenti")

    with st.expander("⚡ Riconfigurazione Rapida", expanded=False):
        # st.warning("Attenzione: Questa operazione sostituirà tutte le scadenze esistenti!")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📅 Pagamento Unico", use_container_width=True):
                st.session_state.current_payment_terms = [{
                    'due_date': invoice_data['document_date'] + timedelta(days=30),
                    'amount': invoice_data['total_amount'],
                    'payment_method': 'Bonifico',
                    'cash_account': 'Banca Intesa',
                    'notes': 'Pagamento unico',
                    'is_paid': False,
                    'payment_date': None
                }]
                st.rerun()

        with col2:
            if st.button("📊 2 Rate Mensili", use_container_width=True):
                terms = auto_split_payment(
                    invoice_data['total_amount'], 2, invoice_data['document_date'], 30
                )
                # Add payment status fields
                for term in terms:
                    term['is_paid'] = False
                    term['payment_date'] = None
                st.session_state.current_payment_terms = terms
                st.rerun()

        with col3:
            if st.button("📈 3 Rate Mensili", use_container_width=True):
                terms = auto_split_payment(
                    invoice_data['total_amount'], 3, invoice_data['document_date'], 30
                )
                # Add payment status fields
                for term in terms:
                    term['is_paid'] = False
                    term['payment_date'] = None
                st.session_state.current_payment_terms = terms
                st.rerun()

        # Custom split
        st.markdown("**Riconfigurazione Personalizzata:**")
        split_col1, split_col2, split_col3 = st.columns([2, 2, 1])

        with split_col1:
            num_installments = st.number_input("Numero rate", min_value=1, max_value=12, value=len(st.session_state.current_payment_terms))

        with split_col2:
            interval_days = st.number_input("Giorni tra rate", min_value=1, max_value=365, value=30)

        with split_col3:
            if st.button("Applica Riconfigurazione", use_container_width=True):
                terms = auto_split_payment(
                    invoice_data['total_amount'], num_installments, invoice_data['document_date'], interval_days
                )
                # Add payment status fields
                for term in terms:
                    term['is_paid'] = False
                    term['payment_date'] = None
                st.session_state.current_payment_terms = terms
                st.rerun()

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
            st.markdown(f"#### Scadenza {i + 1}")

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

            # Payment status (read-only info)
            if term.get('is_paid'):
                st.success(f"✅ Pagato il {term['payment_date'].strftime('%d/%m/%Y') if term.get('payment_date') else 'N/A'}")
            else:
                st.info("⏳ In attesa di pagamento")

            st.markdown("---")

    # Add new payment term button
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Aggiungi Scadenza", use_container_width=True):
            new_term = {
                'due_date': invoice_data['document_date'] + timedelta(days=30),
                'amount': 0.0,
                'payment_method': 'Bonifico',
                'cash_account': 'Banca Intesa',
                'notes': '',
                'is_paid': False,
                'payment_date': None
            }
            st.session_state.current_payment_terms.append(new_term)
            st.rerun()

    with col2:
        if st.session_state.current_payment_terms:
            if st.button("Dividi Importo tra scadenze", use_container_width=True):
                if len(st.session_state.current_payment_terms) > 0:
                    terms = auto_split_payment(
                        invoice_data['total_amount'],
                        len(st.session_state.current_payment_terms),
                        invoice_data['document_date']
                    )
                    # Add payment status fields
                    for term in terms:
                        term['is_paid'] = False
                        term['payment_date'] = None
                    st.session_state.current_payment_terms = terms
                    st.rerun()

    # Save buttons
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Salva Modifiche", type="primary", use_container_width=True):
            is_valid, errors = validate_payment_terms(st.session_state.current_payment_terms, invoice_data['total_amount'])

            if not is_valid:
                for error in errors:
                    st.error(error)
            else:
                if save_payment_terms_to_db(supabase_client, user_id, invoice_data['id'], st.session_state.current_payment_terms):
                    st.success(f"✅ Scadenze modificate con successo!")
                    time.sleep(2)
                    st.session_state.current_payment_terms = []
                    st.session_state.show_payment_form = False
                    st.rerun()

    with col2:
        if st.button("❌ Annulla Modifiche", use_container_width=True):
            st.session_state.current_payment_terms = []
            st.rerun()

def render_payment_terms_view(supabase_client, user_id: str, invoice_data: Dict) -> None:
    """Render payment terms view for an existing invoice"""

    # st.subheader("💰 Visualizza e Modifica Scadenze di Pagamento")
    #
    # # Display invoice info
    # col1, col2, col3 = st.columns(3)
    # with col1:
    #     st.metric("📄 Fattura", invoice_data['invoice_number'])
    # with col2:
    #     st.metric("💰 Importo Totale", f"€ {invoice_data['total_amount']:,.2f}")
    # with col3:
    #     st.metric("📅 Data", invoice_data['document_date'].strftime('%d/%m/%Y'))

    # Load payment terms from database
    payment_terms = load_payment_terms_from_db(supabase_client, user_id, invoice_data['id'])

    if not payment_terms:
        st.warning("⚠️ Nessuna scadenza configurata per questa fattura.")

        col1, col2 = st.columns([1, 1])

        with col1:
            st.info("**Per aggiungere nuove scadenze:**")
            if st.button("➕ Vai alla Pagina di Aggiunta", type="primary", use_container_width=True):
                st.info("🔄 Reindirizzamento alla pagina di aggiunta...")
                st.markdown("**Nota:** Implementare la navigazione alla pagina `deadlines_add.py`")

        with col2:
            st.info("**Per creare scadenze velocemente:**")
            if st.button("⚡ Crea Pagamento Unico", use_container_width=True):
                # Quick create single payment
                single_term = [{
                    'due_date': invoice_data['document_date'] + timedelta(days=30),
                    'amount': invoice_data['total_amount'],
                    'payment_method': 'Bonifico',
                    'cash_account': 'Banca Intesa',
                    'notes': 'Pagamento unico creato rapidamente',
                    'is_paid': False
                }]

                if save_payment_terms_to_db(supabase_client, user_id, invoice_data['id'], single_term):
                    st.success("✅ Pagamento unico creato!")
                    st.rerun()

        return

    # Payment summary
    summary = get_invoice_payment_summary(supabase_client, user_id, invoice_data['id'])
    #
    # st.markdown("### 📊 Riepilogo Pagamenti")
    # col1, col2, col3, col4 = st.columns(4)
    #
    # with col1:
    #     st.metric("Scadenze Totali", summary['total_terms'])
    # with col2:
    #     st.metric("Scadenze Pagate", summary['paid_terms'], delta=f"€ {summary['paid_amount']:,.2f}")
    # with col3:
    #     st.metric("Scadenze in Attesa", summary['pending_terms'], delta=f"€ {summary['pending_amount']:,.2f}")
    # with col4:
    #     if summary['overdue_terms'] > 0:
    #         st.metric("Scadute", summary['overdue_terms'], delta=f"€ {summary['overdue_amount']:,.2f}", delta_color="inverse")
    #     else:
    #         st.metric("Scadute", 0, delta="€ 0.00")


    # Payment terms table
    st.write(" ")
    st.write("Elenco Scadenze")

    # Create DataFrame for display
    terms_data = []
    for term in payment_terms:
        status = "✅ Pagato" if term['is_paid'] else "⏳ In Attesa"
        if not term['is_paid'] and term['due_date'] < date.today():
            status = "❌ Scaduto"

        terms_data.append({
            'Data Scadenza': term['due_date'].strftime('%d/%m/%Y'),
            'Importo €': f"{term['amount']:,.2f}",
            'Modalità': term['payment_method'],
            'Cassa': term['cash_account'],
            'Note': term.get('notes', ''),
            'Stato': status,
            'Data Pagamento': term['payment_date'].strftime('%d/%m/%Y') if term.get('payment_date') else '',
            '_id': term['id'],
            '_is_paid': term['is_paid']
        })

    if terms_data:
        df = pd.DataFrame(terms_data)

        # Display table
        display_df = df.drop(['_id', '_is_paid'], axis=1)
        st.dataframe(display_df, use_container_width=True)

        # # Payment status update section
        # st.markdown("### ✅ Aggiorna Stato Pagamento")
        #
        # # Select term to update
        # term_options = [f"{row['Data Scadenza']} - € {row['Importo €']} - {row['Modalità']}" for _, row in df.iterrows()]
        # selected_term = st.selectbox("Seleziona scadenza:", [""] + term_options)
        #
        # if selected_term:
        #     selected_index = term_options.index(selected_term)
        #     term_id = df.iloc[selected_index]['_id']
        #     current_status = df.iloc[selected_index]['_is_paid']
        #
        #     col1, col2 = st.columns(2)
        #
        #     with col1:
        #         new_status = st.selectbox(
        #             "Nuovo stato:",
        #             ["In Attesa", "Pagato"],
        #             index=1 if current_status else 0
        #         )
        #         is_paid = new_status == "Pagato"
        #
        #     with col2:
        #         payment_date = None
        #         if is_paid:
        #             payment_date = st.date_input("Data pagamento:", value=date.today())
        #
        #     if st.button("💾 Aggiorna Stato", type="primary"):
        #         if update_payment_status(supabase_client, user_id, term_id, is_paid, payment_date):
        #             st.success("✅ Stato aggiornato con successo!")
        #             st.rerun()

    # Action buttons
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("✏️ Modifica Scadenze", type="primary", use_container_width=True):
            st.session_state.show_payment_form = True
            st.rerun()

    with col2:
        if st.button("🗑️ Elimina Tutte le Scadenze", use_container_width=True):
            if 'confirm_delete' not in st.session_state:
                st.session_state.confirm_delete = False

            if not st.session_state.confirm_delete:
                if st.button("⚠️ Conferma Eliminazione", type="secondary"):
                    st.session_state.confirm_delete = True
                    st.rerun()
            else:
                try:
                    supabase_client.table('payment_terms').delete().eq('user_id', user_id).eq('invoice_id', invoice_data['id']).execute()
                    st.session_state.confirm_delete = False
                    st.success("✅ Tutte le scadenze sono state eliminate!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore nell'eliminazione: {str(e)}")

def main():
    """Main function for modifying payment terms"""

    st.set_page_config(
        page_title="Modifica Scadenze Pagamento",
        page_icon="✏️",
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

    st.subheader("Modifica Scadenze di Pagamento")
    # st.markdown("### Questa pagina è dedicata alla modifica di scadenze di pagamento esistenti")

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

            # Show invoice type info
            invoice_type_emoji = "📤" if invoice_data['invoice_type'] == 'emesse' else "📥"
            invoice_type_text = "Fattura Emessa" if invoice_data['invoice_type'] == 'emesse' else "Fattura Ricevuta"
            # st.info(f"{invoice_type_emoji} Stai modificando scadenze per una **{invoice_type_text}**")

            # Load existing payment terms
            payment_terms = load_payment_terms_from_db(supabase_client, user_id, invoice_data['id'])

            # Check if we should show the modification form or the view
            if st.session_state.get('show_payment_form', False):
                render_payment_terms_modification_form(supabase_client, user_id, invoice_data, payment_terms)

                # if st.button("🔙 Torna alla Visualizzazione"):
                #     st.session_state.show_payment_form = False
                #     st.session_state.current_payment_terms = []
                #     st.rerun()
            else:
                render_payment_terms_view(supabase_client, user_id, invoice_data)

    except Exception as e:
        st.error(f"Errore nel caricamento delle fatture: {str(e)}")

if __name__ == "__main__":
    main()