import streamlit as st
import pandas as pd
from decimal import Decimal, getcontext, ROUND_HALF_UP
from datetime import date, datetime, timedelta
from typing import List, Dict
import time

getcontext().prec = 2

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

def delete_all_payment_terms(supabase_client, user_id: str, invoice_id: str) -> bool:
    """Delete all payment terms for a specific invoice"""
    try:
        supabase_client.table('payment_terms').delete().eq('user_id', user_id).eq('invoice_id', invoice_id).execute()
        return True
    except Exception as e:
        st.error(f"Errore nell'eliminazione delle scadenze: {str(e)}")
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

def render_payment_terms_deletion_page(supabase_client, user_id: str, invoice_data: Dict) -> None:
    """Render the payment terms deletion page"""

    # st.subheader("🗑️ Elimina Tutte le Scadenze di Pagamento")
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

    # Load payment terms from database
    payment_terms = load_payment_terms_from_db(supabase_client, user_id, invoice_data['id'])

    if not payment_terms:
        st.info("ℹ️ Questa fattura non ha scadenze di pagamento configurate.")

        # col1, col2, col3 = st.columns([1, 1, 1])
        #
        # with col1:
        #     st.info("**Per aggiungere scadenze:**")
        #     if st.button("➕ Vai alla Pagina di Aggiunta", type="primary", use_container_width=True):
        #         st.info("🔄 Reindirizzamento alla pagina di aggiunta...")
        #         st.markdown("**Nota:** Implementare la navigazione alla pagina `deadlines_add.py`")
        #
        # with col2:
        #     st.info("**Per visualizzare fatture:**")
        #     if st.button("👁️ Visualizza Altre Fatture", use_container_width=True):
        #         st.info("🔄 Seleziona un'altra fattura dall'elenco sopra")
        #
        # with col3:
        #     st.info("**Per tornare indietro:**")
        #     if st.button("🔙 Menu Principale", use_container_width=True):
        #         st.info("🔄 Reindirizzamento al menu principale...")

        return

    # Payment summary
    summary = get_invoice_payment_summary(supabase_client, user_id, invoice_data['id'])

    st.write(" ")
    st.write("Riepilogo Scadenze da Eliminare")
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

    # Payment terms preview table
    # st.markdown("### 📋 Anteprima Scadenze da Eliminare")

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
            'Data Pagamento': term['payment_date'].strftime('%d/%m/%Y') if term.get('payment_date') else ''
        })

    if terms_data:
        df = pd.DataFrame(terms_data)
        st.dataframe(df, use_container_width=True)

    # Warning messages
    st.markdown("---")

    # Check if there are paid terms
    has_paid_terms = summary['paid_terms'] > 0
    has_pending_terms = summary['pending_terms'] > 0

    # if has_paid_terms and has_pending_terms:
    #     st.error("Questa fattura contiene sia scadenze già pagate che scadenze in attesa!")
    #     st.error("L'eliminazione di tutte le scadenze cancellerà anche la cronologia dei pagamenti già effettuati!")
    # elif has_paid_terms:
    #     st.warning("Questa fattura contiene scadenze già pagate!")
    #     st.warning("L'eliminazione cancellerà anche la cronologia dei pagamenti effettuati!")
    # elif has_pending_terms:
    #     st.warning("Questa fattura contiene scadenze di pagamento in attesa.")

    # st.warning("❗ **Questa azione non può essere annullata!**")
    # st.info("💡 **Suggerimento**: Se vuoi modificare le scadenze, usa la pagina di modifica invece di eliminarle.")

    # Deletion process
    st.markdown("#### Processo di Eliminazione")

    # Initialize deletion confirmation state
    if 'deletion_confirmed' not in st.session_state:
        st.session_state.deletion_confirmed = False
    if 'final_confirmation' not in st.session_state:
        st.session_state.final_confirmation = False

    # Step 1: Initial confirmation
    if not st.session_state.deletion_confirmed:
        # st.markdown("#### Passaggio 1: Conferma Iniziale")

        col1, col2 = st.columns([2, 1])

        with col1:
            # st.write("Sei sicuro di voler eliminare **TUTTE** le scadenze di pagamento per questa fattura?")

            # Show consequences
            consequences = []
            if has_paid_terms:
                consequences.append(f"• Verranno eliminate {summary['paid_terms']} scadenze già pagate (€ {summary['paid_amount']:,.2f})")
            if has_pending_terms:
                consequences.append(f"• Verranno eliminate {summary['pending_terms']} scadenze in attesa (€ {summary['pending_amount']:,.2f})")
            consequences.append("• La cronologia completa dei pagamenti sarà eliminata")

            st.markdown("**Conseguenze dell'eliminazione:**")
            for consequence in consequences:
                st.write(consequence)

        with col2:
            if st.button("✅ Sì, Procedi", type="secondary", use_container_width=True):
                st.session_state.deletion_confirmed = True
                with st.spinner("🗑️ Eliminazione in corso..."):
                    if delete_all_payment_terms(supabase_client, user_id, invoice_data['id']):
                        st.success("✅ **Tutte le scadenze sono state eliminate con successo!**")

                        # Reset states
                        st.session_state.deletion_confirmed = False
                        st.session_state.final_confirmation = False

                        # Show success message and reload
                        st.info("🔄 La pagina verrà ricaricata automaticamente per mostrare lo stato aggiornato...")

                        # Auto-reload the page after a short delay
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("❌ Errore durante l'eliminazione.")
                        # Reset states to allow retry
                        st.session_state.final_confirmation = False

            if st.button("❌ No, Annulla", use_container_width=True):
                st.success("✅ Operazione annullata. Nessuna scadenza è stata eliminata.")
                # st.info("💡 Puoi selezionare un'altra fattura o utilizzare i pulsanti di navigazione.")

    # Step 2: Final confirmation
    elif st.session_state.deletion_confirmed and not st.session_state.final_confirmation:
        st.markdown("#### Passaggio 2: Conferma Finale")

        st.error("🚨 **ULTIMA POSSIBILITÀ DI ANNULLARE**")
        st.write("Questa è l'ultima conferma prima dell'eliminazione definitiva.")

        # Show summary of what will be deleted
        st.markdown("**Riepilogo eliminazione:**")
        st.write(f"• Fattura: **{invoice_data['invoice_number']}**")
        st.write(f"• Scadenze totali da eliminare: **{summary['total_terms']}**")
        st.write(f"• Valore totale: **€ {summary['total_amount']:,.2f}**")

        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            if st.button("🗑️ ELIMINA DEFINITIVAMENTE", type="primary", use_container_width=True):
                st.session_state.final_confirmation = True
                st.rerun()

        with col2:
            if st.button("🔙 Torna al Passaggio 1", use_container_width=True):
                st.session_state.deletion_confirmed = False
                st.rerun()

        with col3:
            if st.button("❌ Annulla Tutto", use_container_width=True):
                st.session_state.deletion_confirmed = False
                st.session_state.final_confirmation = False
                st.rerun()

    # Step 3: Execute deletion
    elif st.session_state.final_confirmation:
        st.markdown("#### Passaggio 3: Esecuzione")



def main():
    """Main function for deleting payment terms"""

    st.set_page_config(
        page_title="Elimina Scadenze Pagamento",
        page_icon="🗑️",
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

    st.subheader("Elimina Scadenze di Pagamento")

    # Warning banner
    st.error("Questa operazione elimina definitivamente TUTTE le scadenze e non può essere annullata!")

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

            # Reset confirmation states when switching invoices
            if 'last_selected_invoice' not in st.session_state or st.session_state.last_selected_invoice != selected_invoice:
                st.session_state.deletion_confirmed = False
                st.session_state.final_confirmation = False
                st.session_state.last_selected_invoice = selected_invoice

            # Show invoice type info
            invoice_type_emoji = "📤" if invoice_data['invoice_type'] == 'emesse' else "📥"
            invoice_type_text = "Fattura Emessa" if invoice_data['invoice_type'] == 'emesse' else "Fattura Ricevuta"
            # st.info(f"{invoice_type_emoji} Stai eliminando scadenze da una **{invoice_type_text}**")

            render_payment_terms_deletion_page(supabase_client, user_id, invoice_data)

    except Exception as e:
        st.error(f"Errore nel caricamento delle fatture: {str(e)}")

if __name__ == "__main__":
    main()