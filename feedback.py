import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os

def send_email_feedback(feedback_data):
    """Send feedback via email using SMTP"""
    try:
        # Email configuration (you can use environment variables)
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        email_address = os.getenv("FEEDBACK_EMAIL", "your-email@gmail.com")
        email_password = os.getenv("EMAIL_PASSWORD", "your-app-password")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = email_address
        msg['To'] = email_address  # Send to yourself
        msg['Subject'] = f"[Kruscotto Feedback] {feedback_data['type']} - {feedback_data['subject']}"
        
        # Email body
        body = f"""
Nuovo feedback ricevuto da Kruscotto:

📋 DETTAGLI:
- Tipo: {feedback_data['type']}
- Oggetto: {feedback_data['subject']}
- Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}

👤 UTENTE:
- Nome: {feedback_data['name']}
- Email: {feedback_data['email']}
- Azienda: {feedback_data.get('company', 'Non specificata')}

💬 MESSAGGIO:
{feedback_data['message']}

🔧 INFO TECNICHE:
- User Agent: {feedback_data.get('user_agent', 'Non disponibile')}
- Timestamp: {feedback_data['timestamp']}

---
Questo messaggio è stato inviato automaticamente dal sistema di feedback di Kruscotto.
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_address, email_password)
        text = msg.as_string()
        server.sendmail(email_address, email_address, text)
        server.quit()
        
        return True, "Feedback inviato con successo!"
        
    except Exception as e:
        return False, f"Errore nell'invio: {str(e)}"

def save_feedback_to_database(feedback_data):
    """Save feedback to database (optional)"""
    # This would be implemented if you want to store feedback in your database
    # using your Supabase client
    try:
        # Example implementation:
        # supabase = get_supabase_client()
        # result = supabase.table('feedback').insert(feedback_data).execute()
        # return result.data is not None
        
        # For now, just return True
        return True
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        return False

def feedback_form():
    """Main feedback form component"""
    st.title("💬 Invia Feedback")
    st.write("Aiutaci a migliorare Kruscotto condividendo i tuoi suggerimenti, segnalazioni di bug o richieste di funzionalità.")
    
    with st.form("feedback_form", clear_on_submit=True):
        # Feedback type
        feedback_type = st.selectbox(
            "Tipo di feedback *",
            [
                "💡 Suggerimento",
                "🐛 Segnalazione Bug",
                "🆘 Richiesta Supporto",
                "🚀 Richiesta Funzionalità",
                "📝 Commento Generale",
                "⭐ Recensione"
            ],
            help="Seleziona il tipo di feedback che vuoi inviare"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input(
                "Nome *",
                placeholder="Il tuo nome",
                help="Come dovremmo chiamarti?"
            )
            
        with col2:
            email = st.text_input(
                "Email *",
                placeholder="tua@email.com",
                help="Per poterti ricontattare se necessario"
            )
        
        company = st.text_input(
            "Azienda (opzionale)",
            placeholder="Nome della tua azienda",
            help="Aiutaci a capire meglio il tuo contesto lavorativo"
        )
        
        subject = st.text_input(
            "Oggetto *",
            placeholder="Breve descrizione del tuo feedback",
            help="Riassumi in poche parole il tuo messaggio"
        )
        
        message = st.text_area(
            "Messaggio *",
            placeholder="Descrivi dettagliatamente il tuo feedback, bug o suggerimento...",
            height=150,
            help="Più dettagli fornisci, meglio possiamo aiutarti!"
        )
        
        # Additional options for bug reports
        if "Bug" in feedback_type:
            st.markdown("### 🔍 Informazioni aggiuntive per bug")
            
            col1, col2 = st.columns(2)
            with col1:
                severity = st.selectbox(
                    "Gravità del bug",
                    ["🟢 Bassa", "🟡 Media", "🟠 Alta", "🔴 Critica"],
                    help="Quanto impatta questo bug sul tuo lavoro?"
                )
            
            with col2:
                reproducible = st.selectbox(
                    "È riproducibile?",
                    ["✅ Sempre", "🔄 A volte", "❓ Non so", "❌ Mai"],
                    help="Riesci a far riapparire il bug?"
                )
            
            steps = st.text_area(
                "Passi per riprodurre il bug (opzionale)",
                placeholder="1. Vai alla pagina...\n2. Clicca su...\n3. Vedi che...",
                help="Aiutaci a riprodurre il problema"
            )
        
        # Priority for feature requests
        if "Funzionalità" in feedback_type:
            priority = st.selectbox(
                "Priorità della richiesta",
                ["🔥 Molto alta", "⬆️ Alta", "➡️ Media", "⬇️ Bassa"],
                help="Quanto è importante questa funzionalità per te?"
            )
        
        # Rating for reviews
        if "Recensione" in feedback_type:
            rating = st.select_slider(
                "Valutazione complessiva",
                options=["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"],
                value="⭐⭐⭐⭐",
                help="Come valuti la tua esperienza con Kruscotto?"
            )
        
        # Privacy notice
        st.markdown("---")
        privacy_accepted = st.checkbox(
            "Accetto che i miei dati vengano utilizzati per rispondere al feedback *",
            help="I tuoi dati saranno utilizzati solo per gestire la tua richiesta"
        )
        
        # Submit button
        submitted = st.form_submit_button(
            "📤 Invia Feedback",
            type="primary",
            use_container_width=True
        )
        
        if submitted:
            # Validation
            if not all([name, email, subject, message, privacy_accepted]):
                st.error("⚠️ Per favore compila tutti i campi obbligatori e accetta la privacy policy")
            elif "@" not in email or "." not in email:
                st.error("⚠️ Inserisci un indirizzo email valido")
            else:
                # Prepare feedback data
                feedback_data = {
                    'type': feedback_type,
                    'name': name,
                    'email': email,
                    'company': company,
                    'subject': subject,
                    'message': message,
                    'timestamp': datetime.now().isoformat(),
                    'user_agent': st.context.headers.get('User-Agent', 'Unknown') if hasattr(st.context, 'headers') else 'Unknown'
                }
                
                # Add specific fields based on feedback type
                if "Bug" in feedback_type:
                    feedback_data.update({
                        'severity': severity,
                        'reproducible': reproducible,
                        'steps': steps if 'steps' in locals() else ''
                    })
                
                if "Funzionalità" in feedback_type:
                    feedback_data['priority'] = priority if 'priority' in locals() else ''
                
                if "Recensione" in feedback_type:
                    feedback_data['rating'] = rating if 'rating' in locals() else ''
                
                # Send feedback
                with st.spinner("Invio del feedback in corso..."):
                    # Try to send email
                    email_success, email_message = send_email_feedback(feedback_data)
                    
                    # Try to save to database (optional)
                    db_success = save_feedback_to_database(feedback_data)
                    
                    if email_success:
                        st.success("✅ " + email_message)
                        st.balloons()
                        
                        # Show next steps
                        st.info(
                            "📋 **Prossimi passi:**\n"
                            "- Riceverai una conferma via email entro 24 ore\n"
                            "- Per richieste urgenti, rispondiamo entro 2-3 giorni lavorativi\n"
                            "- Per suggerimenti, valuteremo l'implementazione nel prossimo rilascio"
                        )
                        
                        # Contact info
                        st.markdown("---")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("📧 **Email diretta:** assistenza@kruscotto.it")
                        with col2:
                            st.markdown("🕐 **Orari supporto:** Lun-Ven 9:00-18:00")
                    else:
                        st.error("❌ " + email_message)
                        st.error("Se il problema persiste, scrivi direttamente a: assistenza@kruscotto.it")

def feedback_sidebar():
    """Compact feedback widget for sidebar"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💬 Feedback Rapido")
    
    with st.sidebar.form("quick_feedback"):
        quick_message = st.text_area(
            "Invia un suggerimento veloce:",
            placeholder="Il tuo feedback...",
            height=100
        )
        
        quick_email = st.text_input(
            "Email (opzionale):",
            placeholder="per risposta"
        )
        
        if st.form_submit_button("Invia", use_container_width=True):
            if quick_message.strip():
                feedback_data = {
                    'type': '💬 Feedback Rapido',
                    'name': 'Utente Anonimo',
                    'email': quick_email or 'Non fornita',
                    'company': '',
                    'subject': 'Feedback Rapido',
                    'message': quick_message,
                    'timestamp': datetime.now().isoformat(),
                    'user_agent': 'Sidebar Widget'
                }
                
                success, message = send_email_feedback(feedback_data)
                if success:
                    st.sidebar.success("Grazie per il feedback!")
                else:
                    st.sidebar.error("Errore nell'invio")
            else:
                st.sidebar.error("Scrivi un messaggio")

# Main function for standalone use
def main():
    st.set_page_config(
        page_title="Feedback - Kruscotto",
        page_icon="💬",
        layout="wide"
    )
    
    feedback_form()
    
    # Show recent feedback stats (optional)
    with st.expander("📊 Statistiche Feedback"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Feedback questo mese", "47", "+12")
        with col2:
            st.metric("Bug risolti", "23", "+8")
        with col3:
            st.metric("Tempo medio risposta", "2.1 giorni", "-0.3")

if __name__ == "__main__":
    main()