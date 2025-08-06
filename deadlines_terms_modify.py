import streamlit as st
import pandas as pd
from decimal import Decimal, getcontext, ROUND_HALF_UP
from datetime import date, datetime, timedelta
from typing import List, Dict, Tuple
import plotly.express as px
import uuid

getcontext().prec = 2

# Constants
PAYMENT_METHODS = ['Bonifico', 'Contanti', 'Assegno', 'Carta di credito', 'RID', 'Altro']
CASH_ACCOUNTS = ['Banca Intesa', 'Cassa Contanti', 'Cassa Generica', 'INTESA SAN PAOLO']

def load_payment_terms_from_db(supabase_client, user_id: str, invoice_id: str) -> List[Dict]:
    """Load payment terms from database for a specific invoice"""
    try:
        result = supabase_client.table('payment_terms').select('*').eq('user_id', user_id).eq('invoice_id', invoice_id).order('data_scadenza_pagamento').execute()

        terms = []
        for row in result.data:
            terms.append({
                'id': row['id'],
                'data_scadenza_pagamento': datetime.strptime(row['data_scadenza_pagamento'], '%Y-%m-%d').date(),
                'importo_pagamento_rata': float(row['importo_pagamento_rata']),
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
                'importo_totale_documento': 0,
                'paid_amount': 0,
                'pending_amount': 0,
                'overdue_terms': 0,
                'overdue_amount': 0
            }

        total_terms = len(result.data)
        paid_terms = sum(1 for term in result.data if term['is_paid'])
        pending_terms = total_terms - paid_terms

        importo_totale_documento = sum(Decimal(str(term['importo_pagamento_rata'])) for term in result.data)
        paid_amount = sum(Decimal(str(term['importo_pagamento_rata'])) for term in result.data if term['is_paid'])
        pending_amount = importo_totale_documento - paid_amount

        # Calculate overdue
        today = date.today()
        overdue_terms = 0
        overdue_amount = Decimal('0')

        for term in result.data:
            if not term['is_paid']:
                data_scadenza_pagamento = datetime.strptime(term['data_scadenza_pagamento'], '%Y-%m-%d').date()
                if data_scadenza_pagamento < today:
                    overdue_terms += 1
                    overdue_amount += Decimal(str(term['importo_pagamento_rata']))

        return {
            'total_terms': total_terms,
            'paid_terms': paid_terms,
            'pending_terms': pending_terms,
            'importo_totale_documento': float(importo_totale_documento),
            'paid_amount': float(paid_amount),
            'pending_amount': float(pending_amount),
            'overdue_terms': overdue_terms,
            'overdue_amount': float(overdue_amount)
        }

    except Exception as e:
        st.error(f"Errore nel calcolo del riepilogo pagamenti: {str(e)}")
        return {}

def render_payment_terms_view(supabase_client, user_id: str, invoice_data: Dict) -> None:
    """Render payment terms view for an existing invoice"""

    # st.subheader("Aggiorna Stato Pagamenti")

    # # Display invoice info
    # col1, col2, col3 = st.columns(3)
    # with col1:
    #     st.metric("📄 Fattura", invoice_data['numero_fattura'])
    # with col2:
    #     st.metric("💰 Importo Totale", f"€ {invoice_data['importo_totale_documento']:,.2f}")
    # with col3:
    #     st.metric("📅 Data", invoice_data['data_documento'].strftime('%d/%m/%Y'))

    # Load payment terms from database
    payment_terms = load_payment_terms_from_db(supabase_client, user_id, invoice_data['id'])

    if not payment_terms:
        st.warning("⚠️ Nessuna scadenza configurata per questa fattura.")

        # st.info("**Per configurare le scadenze, utilizzare la pagina dedicata alla gestione delle scadenze.**")
        #
        # col1, col2 = st.columns([1, 1])
        # with col1:
        #     if st.button("➕ Vai alla Pagina di Aggiunta Scadenze", type="primary", use_container_width=True):
        #         st.info("🔄 Reindirizzamento alla pagina di aggiunta...")
        #         st.markdown("**Nota:** Implementare la navigazione alla pagina di aggiunta scadenze")
        # with col2:
        #     if st.button("✏️ Vai alla Pagina di Modifica Scadenze", use_container_width=True):
        #         st.info("🔄 Reindirizzamento alla pagina di modifica...")
        #         st.markdown("**Nota:** Implementare la navigazione alla pagina di modifica scadenze")

        return

    # Payment summary
    summary = get_invoice_payment_summary(supabase_client, user_id, invoice_data['id'])

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
        if not term['is_paid'] and term['data_scadenza_pagamento'] < date.today():
            status = "❌ Scaduto"

        terms_data.append({
            'Data Scadenza': term['data_scadenza_pagamento'].strftime('%d/%m/%Y'),
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

        # Payment status update section - This is the main focus of this page
        # st.markdown("### ✅ Aggiorna Stato Pagamento")
        # st.markdown("**Questa pagina è dedicata esclusivamente all'aggiornamento dello stato di pagamento delle singole scadenze.**")

        # Select term to update
        term_options = [f"{row['Data Scadenza']} - € {row['Importo €']} - {row['Modalità']}" for _, row in df.iterrows()]
        selected_term = st.selectbox("Seleziona scadenza da aggiornare:", [""] + term_options)

        if selected_term:
            selected_index = term_options.index(selected_term)
            term_id = df.iloc[selected_index]['_id']
            current_status = df.iloc[selected_index]['_is_paid']

            # # Show current status
            # if current_status:
            #     st.success(f"✅ **Stato attuale**: Pagato")
            # else:
            #     if df.iloc[selected_index]['Data Scadenza']:
            #         data_scadenza_pagamento_str = df.iloc[selected_index]['Data Scadenza']
            #         data_scadenza_pagamento = datetime.strptime(data_scadenza_pagamento_str, '%d/%m/%Y').date()
            #         if data_scadenza_pagamento < date.today():
            #             st.error(f"❌ **Stato attuale**: Scaduto (scadenza: {data_scadenza_pagamento_str})")
            #         else:
            #             st.info(f"⏳ **Stato attuale**: In Attesa (scadenza: {data_scadenza_pagamento_str})")

            col1, col2 = st.columns(2)

            with col1:
                new_status = st.selectbox(
                    "Nuovo stato:",
                    ["In Attesa", "Pagato"],
                    index=1 if current_status else 0
                )
                is_paid = new_status == "Pagato"

            with col2:
                payment_date = None
                if is_paid:
                    # Default to today for new payments, or existing payment date
                    existing_payment_date = datetime.strptime(df.iloc[selected_index]['Data Pagamento'], '%d/%m/%Y').date() if df.iloc[selected_index]['Data Pagamento'] else date.today()
                    payment_date = st.date_input("Data pagamento:", value=existing_payment_date)
                else:
                    st.write("") # Spacing
                    # st.info("💡 La data di pagamento verrà rimossa se cambi lo stato a 'In Attesa'")

            # Only show update button if there's a change
            status_changed = is_paid != current_status
            if status_changed or (is_paid and payment_date):
                if st.button("💾 Aggiorna Stato", type="primary", use_container_width=True):
                    if update_payment_status(supabase_client, user_id, term_id, is_paid, payment_date):
                        if is_paid:
                            st.success(f"✅ Scadenza marcata come pagata il {payment_date.strftime('%d/%m/%Y')}!")
                        else:
                            st.success("✅ Scadenza marcata come in attesa!")
                        
                        st.rerun()
            else:
                # st.info("💡 Seleziona una scadenza e modifica lo stato per vedere il pulsante di aggiornamento")
                pass

        # Quick actions for multiple payments
        # st.markdown("---")
        # st.markdown("### ⚡ Azioni Rapide")
        #
        # # Count unpaid terms
        # unpaid_terms = [term for term in payment_terms if not term['is_paid']]
        #
        # if unpaid_terms:
        #     col1, col2 = st.columns(2)
        #
        #     with col1:
        #         st.info(f"**{len(unpaid_terms)} scadenze non pagate**")
        #         if st.button("💰 Marca Tutto Come Pagato Oggi", use_container_width=True):
        #             success_count = 0
        #             for term in unpaid_terms:
        #                 if update_payment_status(supabase_client, user_id, term['id'], True, date.today()):
        #                     success_count += 1
        #
        #             if success_count == len(unpaid_terms):
        #                 st.success(f"✅ Tutte le {success_count} scadenze sono state marchiate come pagate!")
        #
        #                 st.rerun()
        #             else:
        #                 st.warning(f"⚠️ {success_count} di {len(unpaid_terms)} scadenze aggiornate con successo")
        #
        #     with col2:
        #         overdue_terms = [term for term in unpaid_terms if term['data_scadenza_pagamento'] < date.today()]
        #         if overdue_terms:
        #             st.warning(f"**{len(overdue_terms)} scadenze scadute**")
        #             if st.button("⚠️ Marca Solo Scadute Come Pagate", use_container_width=True):
        #                 success_count = 0
        #                 for term in overdue_terms:
        #                     if update_payment_status(supabase_client, user_id, term['id'], True, date.today()):
        #                         success_count += 1
        #
        #                 if success_count == len(overdue_terms):
        #                     st.success(f"✅ Tutte le {success_count} scadenze scadute sono state marchiate come pagate!")
        #
        #                     st.rerun()
        #                 else:
        #                     st.warning(f"⚠️ {success_count} di {len(overdue_terms)} scadenze scadute aggiornate")
        #         else:
        #             st.success("✅ **Nessuna scadenza scaduta**")
        # else:
        #     st.success("🎉 **Tutte le scadenze sono già state pagate!**")

def main():
    """Main function for payment status update page"""

    st.set_page_config(
        page_title="Aggiorna Stato Pagamenti",
        page_icon="💳",
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

    st.subheader("Aggiorna Stato Pagamenti")
    # st.markdown("### Questa pagina è dedicata esclusivamente all'aggiornamento dello stato di pagamento delle scadenze")

    try:
        # Load both invoice types
        emesse_invoices_result = supabase_client.table('fatture_emesse').select('*').eq('user_id', user_id).order('data_documento', desc=True).execute()
        ricevute_invoices_result = supabase_client.table('fatture_ricevute').select('*').eq('user_id', user_id).order('data_documento', desc=True).execute()

        # Combine both invoice types into a single list with type identifier
        all_invoice_options = []
        all_invoice_data = []

        # Add emesse invoices
        if emesse_invoices_result.data:
            for inv in emesse_invoices_result.data:
                option_text = f"📤 EMESSA: {inv['numero_fattura']} - € {inv['importo_totale_documento']:,.2f} ({inv['data_documento']})"
                all_invoice_options.append(option_text)
                inv['invoice_type'] = 'emesse'  # Add type identifier
                all_invoice_data.append(inv)

        # Add ricevute invoices
        if ricevute_invoices_result.data:
            for inv in ricevute_invoices_result.data:
                option_text = f"📥 RICEVUTA: {inv['numero_fattura']} - € {inv['importo_totale_documento']:,.2f} ({inv['data_documento']})"
                all_invoice_options.append(option_text)
                inv['invoice_type'] = 'ricevute'  # Add type identifier
                all_invoice_data.append(inv)

        # Check if we have any invoices at all
        if not all_invoice_options:
            st.warning("⚠️ Nessuna fattura trovata. Creare una fattura prima di gestire i pagamenti.")
            return

        # Single selectbox for all invoices
        selected_invoice = st.selectbox("Seleziona Fattura:", [""] + all_invoice_options)

        if selected_invoice:  # Only proceed if something is selected
            selected_index = all_invoice_options.index(selected_invoice)
            invoice_data = all_invoice_data[selected_index]

            # Convert date string to date object
            invoice_data['data_documento'] = datetime.strptime(invoice_data['data_documento'], '%Y-%m-%d').date()

            # Show invoice type info
            invoice_type_emoji = "📤" if invoice_data['invoice_type'] == 'emesse' else "📥"
            invoice_type_text = "Fattura Emessa" if invoice_data['invoice_type'] == 'emesse' else "Fattura Ricevuta"
            # st.info(f"{invoice_type_emoji} Stai aggiornando i pagamenti per una **{invoice_type_text}**")

            render_payment_terms_view(supabase_client, user_id, invoice_data)

    except Exception as e:
        st.error(f"Errore nel caricamento delle fatture: {str(e)}")

if __name__ == "__main__":
    main()