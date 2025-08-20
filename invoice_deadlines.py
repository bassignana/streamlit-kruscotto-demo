import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from decimal import Decimal, getcontext, ROUND_HALF_UP
from typing import Dict, List

from invoice_utils import render_selectable_dataframe
from utils import setup_page

PAYMENT_METHODS = ['Bonifico', 'Contanti', 'Assegno', 'Carta di credito', 'RID', 'Altro']
CASH_ACCOUNTS = ['Banca Intesa', 'Cassa Contanti', 'Cassa Generica', 'INTESA SAN PAOLO']

def auto_split_payment(importo_totale_documento: float, num_installments: int, start_date: date, interval_days: int = 30) -> List[Dict]:
    # Precision 28 is different from decimal places!
    # I need to keep high precision to be able to handle float conversion
    # correctly. Then I can use quantize to force decimal places to two.
    getcontext().prec = 28
    MONEY_QUANTIZE = Decimal('0.01')  # 2 decimal places
    CURRENCY_ROUNDING = ROUND_HALF_UP

    def format_money(amount):
        decimal_amount = Decimal(str(amount))
        return decimal_amount.quantize(MONEY_QUANTIZE, rounding=CURRENCY_ROUNDING)

    if num_installments <= 0:
        return []

    total_decimal = format_money(importo_totale_documento)
    amount_per_installment = format_money(total_decimal / num_installments)

    terms = []
    total_allocated = Decimal('0.00')

    for i in range(num_installments):
        # Last installment gets the remainder to avoid rounding errors
        if i == num_installments - 1:
            installment_amount = total_decimal - total_allocated
        else:
            installment_amount = amount_per_installment
            total_allocated += installment_amount

        term = {
            'rfe_data_scadenza_pagamento': start_date + timedelta(days=interval_days * (i + 1)),
            'rfe_importo_pagamento_rata': float(installment_amount),
            'rfe_nome_cassa': 'Banca Intesa',
            'rfe_notes': f'Rata {i + 1} di {num_installments}',
            'rfe_data_pagamento_rata': None  # Not paid yet
        }
        terms.append(term)

    return terms

def validate_payment_terms(payment_terms: List[Dict], total_amount: float) -> tuple[bool, List[str]]:
    """Validate payment terms configuration"""
    errors = []

    if not payment_terms:
        errors.append("Devi configurare almeno una scadenza di pagamento")
        return False, errors

    # Check total amount matches
    total_configured = sum(Decimal(str(term['rfe_importo_pagamento_rata'])) for term in payment_terms)
    total_expected = Decimal(str(total_amount))

    if abs(total_configured - total_expected) >= Decimal('0.01'):
        errors.append(f"La somma delle scadenze (€ {total_configured:.2f}) non corrisponde all'importo totale (€ {total_expected:.2f})")

    # Check all amounts are positive
    for i, term in enumerate(payment_terms):
        if term['rfe_importo_pagamento_rata'] <= 0:
            errors.append(f"L'importo della scadenza {i + 1} deve essere maggiore di zero")

    return len(errors) == 0, errors

def save_payment_terms_to_db(supabase_client, user_id: str, invoice_key: Dict, payment_terms: List[Dict]) -> bool:
    try:
        # TODO; put it in a transaction
        # First, delete existing payment terms for this invoice
        supabase_client.table('rate_fatture_emesse').delete().eq('user_id', user_id).eq(
            'rfe_partita_iva_prestatore', invoice_key['partita_iva_prestatore']
        ).eq('rfe_numero_fattura', invoice_key['numero_fattura']).eq(
            'rfe_data_documento', invoice_key['data_documento']
        ).execute()

        # Insert new payment terms
        for term in payment_terms:
            term_data = {
                'user_id': user_id,
                'rfe_partita_iva_prestatore': invoice_key['partita_iva_prestatore'],
                'rfe_numero_fattura': invoice_key['numero_fattura'],
                'rfe_data_documento': invoice_key['data_documento'],
                'rfe_data_scadenza_pagamento': term['rfe_data_scadenza_pagamento'].strftime('%Y-%m-%d'),
                'rfe_importo_pagamento_rata': term['rfe_importo_pagamento_rata'],
                'rfe_nome_cassa': term['rfe_nome_cassa'],
                'rfe_notes': term['rfe_notes'],
                'rfe_data_pagamento_rata': term['rfe_data_pagamento_rata'].strftime('%Y-%m-%d') if term['rfe_data_pagamento_rata'] else None
            }
            supabase_client.table('rate_fatture_emesse').insert(term_data).execute()

        return True
    except Exception as e:
        st.error(f"Errore nel salvataggio: {str(e)}")
        return False

def load_existing_payment_terms(supabase_client, user_id: str, invoice_key: Dict) -> List[Dict]:
    """Load existing payment terms for an invoice"""
    try:
        result = supabase_client.table('rate_fatture_emesse').select('*').eq('user_id', user_id).eq(
            'rfe_partita_iva_prestatore', invoice_key['partita_iva_prestatore']
        ).eq('rfe_numero_fattura', invoice_key['numero_fattura']).eq(
            'rfe_data_documento', invoice_key['data_documento']
        ).execute()

        terms = []
        for row in result.data:
            term = {
                'rfe_data_scadenza_pagamento': datetime.strptime(row['rfe_data_scadenza_pagamento'], '%Y-%m-%d').date(),
                'rfe_importo_pagamento_rata': float(row['rfe_importo_pagamento_rata']),
                'rfe_nome_cassa': row['rfe_nome_cassa'] or 'Banca Intesa',
                'rfe_notes': row['rfe_notes'] or '',
                'rfe_data_pagamento_rata': datetime.strptime(row['rfe_data_pagamento_rata'], '%Y-%m-%d').date() if row['rfe_data_pagamento_rata'] else None
            }
            terms.append(term)

        return terms
    except Exception as e:
        st.error(f"Errore nel caricamento: {str(e)}")
        return []



def render_payment_terms_form(supabase_client, user_id: str, importo_totale_documento: float,
                              data_documento: date, invoice_key: Dict) -> None:
    #
    # If I add manually an invoice, I'll not have any corresponding records in the
    # rate_scadenze_emesse. I'll fix this, for now it will stay like this.
    #
    existing_terms = load_existing_payment_terms(supabase_client, user_id, invoice_key)

    if 'edit_payment_terms' not in st.session_state:
        st.session_state.edit_payment_terms = False

    if 'current_payment_terms' not in st.session_state:
        if existing_terms:
            st.session_state.current_payment_terms = existing_terms.copy()
        else:
            # The structure is the same of the downloaded data.
            st.session_state.current_payment_terms = [{
                'rfe_data_scadenza_pagamento': data_documento + timedelta(days=30),
                'rfe_importo_pagamento_rata': importo_totale_documento,
                'rfe_nome_cassa': '',
                'rfe_notes': '',
                'rfe_data_pagamento_rata': None
            }]

    st.markdown("Scadenze Attualmente Configurate:")
    total_configured = sum(term['rfe_importo_pagamento_rata'] for term in existing_terms)
    paid_amount = sum(term['rfe_importo_pagamento_rata'] for term in existing_terms if term['rfe_data_pagamento_rata'])
    unpaid_amount = total_configured - paid_amount

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Importo Totale", f"€ {importo_totale_documento:,.2f}")
    with col2:
        st.metric("Configurato", f"€ {total_configured:,.2f}")

    #
    # For now I remove this because it may be confusing when I'm editing the terms structure
    # but this message is not updating.
    #
    # if abs(total_configured - importo_totale_documento) >= 0.01:
    #     st.warning(f"Differenza tra totale fattura e scadenze configurate: € {total_configured - importo_totale_documento:,.2f}")

    df_display = pd.DataFrame([
        {
            'Scadenza': term['rfe_data_scadenza_pagamento'].strftime('%d/%m/%Y'),
            'Importo': f"€ {term['rfe_importo_pagamento_rata']:,.2f}",
            'Cassa': term['rfe_nome_cassa'],
            'Note': term['rfe_notes'],
            'Pagato': '✅' if term['rfe_data_pagamento_rata'] else '❌',
            'Data Pagamento': term['rfe_data_pagamento_rata'].strftime('%d/%m/%Y') if term['rfe_data_pagamento_rata'] else '-'
        }
        for term in existing_terms
    ])

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # col2 for spacing.
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Aggiungi o Modifica Scadenze", type="primary", use_container_width=True):
            st.session_state.edit_payment_terms = True
            st.session_state.current_payment_terms = existing_terms.copy()
            st.rerun()

    if st.session_state.edit_payment_terms:

        with st.expander("Configurazione Rapida", expanded=True):
            split_col1, split_col2, split_col3 = st.columns([2, 2, 1])

            with split_col1:
                num_installments = st.number_input("Numero rate", min_value=1, max_value=12, value=1)

            with split_col2:
                interval_days = st.number_input("Giorni tra rate", min_value=1, max_value=365, value=30, step=15)

            with split_col3:
                if st.button("Applica Configurazione", use_container_width=True):
                    st.session_state.current_payment_terms = auto_split_payment(
                        importo_totale_documento, num_installments, data_documento, interval_days
                    )
                    st.rerun()

        # Current payment terms configuration
        # if st.session_state.current_payment_terms:
        # TODO; sum and or reminders not calculated correctly. Maybe session state not updated correctly.
        # total_configured = sum(term['rfe_importo_pagamento_rata'] for term in st.session_state.current_payment_terms)
        # remaining = importo_totale_documento - total_configured
        #
        # col1, col2, col3 = st.columns(3)
        # with col1:
        #     st.write("Importo Totale", f"\n € {importo_totale_documento:,.2f}")
        # with col2:
        #     st.write("Importo Configurato", f"\n € {total_configured:,.2f}")
        # with col3:
        #     st.write("Rimanente", f"\n € {remaining:,.2f}")
        #     if abs(remaining) >= 0.01:
        #         st.warning(f"⚠️ Differenza di € {remaining:,.2f}")

        #     # Payment terms list
        for i, term in enumerate(st.session_state.current_payment_terms):
            with st.container():
                st.markdown(f"##### Scadenza {i + 1}")

                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

                with col1:
                    new_date = st.date_input(
                        "Data Scadenza",
                        value=term['rfe_data_scadenza_pagamento'],
                        key=f"date_{i}"
                    )
                    st.session_state.current_payment_terms[i]['rfe_data_scadenza_pagamento'] = new_date

                with col2:
                    new_amount = st.number_input(
                        "Importo (€)",
                        min_value=0.0,
                        value=max(0.0, term['rfe_importo_pagamento_rata']),
                        step=0.01,
                        key=f"amount_{i}"
                    )
                    st.session_state.current_payment_terms[i]['rfe_importo_pagamento_rata'] = new_amount

                with col3:
                    new_cassa = st.selectbox(
                        "Cassa",
                        CASH_ACCOUNTS,
                        index=CASH_ACCOUNTS.index(term['rfe_nome_cassa']) if term['rfe_nome_cassa'] in CASH_ACCOUNTS else 0,
                        key=f"cassa_{i}"
                    )
                    st.session_state.current_payment_terms[i]['rfe_nome_cassa'] = new_cassa

                with col4:
                    st.write("")  # Spacing
                    st.write("")  # Spacing
                    if len(st.session_state.current_payment_terms) > 1:
                        if st.button("🗑️", key=f"remove_{i}", help="Rimuovi scadenza"):
                            st.session_state.current_payment_terms.pop(i)
                            st.rerun()

                # Second row for additional details
                col1, col2, col3 = st.columns([2, 2, 2])

                with col1:
                    new_notes = st.text_input(
                        "Note (opzionale)",
                        value=term.get('rfe_notes', ''),
                        key=f"notes_{i}"
                    )
                    st.session_state.current_payment_terms[i]['rfe_notes'] = new_notes

                with col2:
                    # Payment date (for marking as paid)
                    payment_date = st.date_input(
                        "Data Pagamento (se pagato)",
                        value=term['rfe_data_pagamento_rata'],
                        key=f"payment_date_{i}",
                        help="Lascia vuoto se non ancora pagato"
                    )
                    st.session_state.current_payment_terms[i]['rfe_data_pagamento_rata'] = payment_date

                # with col3:
                #     # Quick pay button
                #     if not term['rfe_data_pagamento_rata']:
                #         if st.button(f"💰 Segna come Pagato Oggi", key=f"pay_today_{i}"):
                #             st.session_state.current_payment_terms[i]['rfe_data_pagamento_rata'] = date.today()
                #             st.rerun()
                #     else:
                #         if st.button(f"❌ Segna come Non Pagato", key=f"unpay_{i}"):
                #             st.session_state.current_payment_terms[i]['rfe_data_pagamento_rata'] = None
                #             st.rerun()

                st.markdown("---")

        # Add new payment term button
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Aggiungi Scadenza", use_container_width=True):
                new_term = {
                    'rfe_data_scadenza_pagamento': data_documento + timedelta(days=30),
                    'rfe_importo_pagamento_rata': 0.0,
                    'rfe_nome_cassa': 'Banca Intesa',
                    'rfe_notes': '',
                    'rfe_data_pagamento_rata': None
                }
                st.session_state.current_payment_terms.append(new_term)
                st.rerun()

        with col2:
            if st.session_state.current_payment_terms:
                if st.button("Dividi Importo tra scadenze", use_container_width=True):
                    if len(st.session_state.current_payment_terms) > 0:
                        # Keep existing payment dates but recalculate amounts
                        payment_dates = [term['rfe_data_pagamento_rata'] for term in st.session_state.current_payment_terms]
                        st.session_state.current_payment_terms = auto_split_payment(
                            importo_totale_documento,
                            len(st.session_state.current_payment_terms),
                            data_documento
                        )
                        # Restore payment dates
                        for i, payment_date in enumerate(payment_dates):
                            if i < len(st.session_state.current_payment_terms):
                                st.session_state.current_payment_terms[i]['rfe_data_pagamento_rata'] = payment_date
                        st.rerun()

        # Save buttons
        if st.session_state.current_payment_terms:
            st.markdown("---")
            col1, col2 = st.columns(2)

            with col1:
                if st.button("💾 Salva Scadenze", type="primary", use_container_width=True):
                    is_valid, errors = validate_payment_terms(st.session_state.current_payment_terms, importo_totale_documento)

                    if not is_valid:
                        for error in errors:
                            st.error(error)
                    else:
                        if save_payment_terms_to_db(supabase_client, user_id, invoice_key, st.session_state.current_payment_terms):
                            st.success(f"✅ Scadenze salvate con successo!")
                            # Clear edit mode and temp data
                            st.session_state.edit_payment_terms = False
                            if 'current_payment_terms' in st.session_state:
                                del st.session_state.current_payment_terms
                            st.rerun()

            with col2:
                if st.button("❌ Annulla", use_container_width=True):
                    # Clear edit mode and temp data
                    st.session_state.edit_payment_terms = False
                    if 'current_payment_terms' in st.session_state:
                        del st.session_state.current_payment_terms
                    st.rerun()

def main():
    user_id, supabase_client, page_can_render = setup_page("Gestione Scadenze")
    emesse, ricevute = st.tabs(["Scadenze Fatture Emesse", "Scadenze Fatture Ricevute"])

    with emesse:
        try:
            invoices_result = supabase_client.table('fatture_emesse').select('*').eq('user_id', user_id).execute()
            if not invoices_result.data:
                st.warning("Nessuna fattura trovata. Creare una fattura prima di gestire le scadenze.")
                return

            # This is for resetting the state of the button press and the state containing
            # the information about the current set of terms when I change selection in the
            # dataframe.
            def state_reset_callback():
                for key in ['edit_payment_terms', 'current_payment_terms']:
                    if key in st.session_state:
                        del st.session_state[key]

                # Calling st.rerun() within a callback is a no-op.
                # st.rerun()

            on_select = state_reset_callback

            selection = render_selectable_dataframe(invoices_result.data, 'single-row', on_select)

            if selection.selection['rows']:
                # Get selected invoice data
                df = pd.DataFrame(invoices_result.data)
                selected_index = selection.selection['rows'][0]  # Get first (and only) selected row.
                selected_invoice = df.iloc[selected_index]

                invoice_key = {
                    'partita_iva_prestatore': selected_invoice['fe_partita_iva_prestatore'],
                    'numero_fattura': selected_invoice['fe_numero_fattura'],
                    'data_documento': selected_invoice['fe_data_documento']
                }

                importo_totale_documento = float(selected_invoice['fe_importo_totale_documento'])
                data_documento = datetime.strptime(selected_invoice['fe_data_documento'], '%Y-%m-%d').date()

                # st.markdown("---")
                # col1, col2, col3 = st.columns(3)
                # with col1:
                #     st.info(f"**Fattura:** {selected_invoice['fe_numero_fattura']}")
                # with col2:
                #     st.info(f"**Data:** {data_documento.strftime('%d/%m/%Y')}")
                # with col3:
                #     st.info(f"**Importo:** € {importo_totale_documento:,.2f}")

                render_payment_terms_form(
                    supabase_client,
                    user_id,
                    importo_totale_documento,
                    data_documento,
                    invoice_key
                )

        except Exception as e:
            st.error(f"Errore nel caricamento delle scadenze: {str(e)}")

    with ricevute:
        pass


if __name__ == "__main__":
    main()