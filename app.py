import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
from database import init_db, get_connection

# Configurazione Pagina Streamlit
st.set_page_config(
    page_title="Gestionale Aziendale & AI",
    page_icon="⚙️",
    layout="wide"
)

# Inizializzazione Database
try:
    init_db()
except Exception as e:
    st.error(f"Impossibile inizializzare il database: {e}")

# Inizializzazione Client Gemini
@st.cache_resource
def get_gemini_client():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.warning("GEMINI_API_KEY non trovata nei secrets.")
        return None
    return genai.Client(api_key=api_key)

client = get_gemini_client()

# Header App
st.title("⚙️ Gestionale Produzione & Preventivi")

# Navigazione a Schede (Tabs)
tab_dash, tab_prodotti, tab_aziende, tab_ai = st.tabs([
    "📊 Dashboard Preventivi", 
    "🏭 Prodotti & Settori", 
    "🏢 Aziende & Operatori", 
    "🤖 Assistente Gemini AI"
])

# ---------------------------------------------------------
# TAB 1: DASHBOARD PREVENTIVI
# ---------------------------------------------------------
with tab_dash:
    st.header("Gestione Preventivi")
    
    with get_connection() as conn:
        df_prev = pd.read_sql("""
            SELECT p.id, a.ragione_sociale, pr.nome as prodotto, p.quantita, 
                   p.prezzo_totale, p.ore_totali_stimate, p.stato 
            FROM preventivi p
            LEFT JOIN aziende a ON p.azienda_id = a.id
            LEFT JOIN prodotti pr ON p.prodotto_id = pr.id
            ORDER BY p.id DESC
        """, conn)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Totale Preventivi", len(df_prev))
    col2.metric("In Attesa", len(df_prev[df_prev['stato'] == 'In attesa']) if not df_prev.empty else 0)
    col3.metric("Approvati", len(df_prev[df_prev['stato'] == 'Approvato']) if not df_prev.empty else 0)

    st.subheader("Elenco Preventivi")
    st.dataframe(df_prev, use_container_width=True)

# ---------------------------------------------------------
# TAB 2: PRODOTTI & SETTORI
# ---------------------------------------------------------
with tab_prodotti:
    st.header("Anagrafica Prodotti")
    
    with st.form("nuovo_prodotto"):
        st.subheader("Aggiungi Nuovo Prodotto")
        nome = st.text_input("Nome Prodotto")
        materiale = st.text_input("Materiale / Trattamento")
        costo_int = st.number_input("Costo Interno (€)", min_value=0.0, step=0.50)
        prezzo_ven = st.number_input("Prezzo Vendita (€)", min_value=0.0, step=0.50)
        submit_prod = st.form_submit_button("Salva Prodotto")
        
        if submit_prod and nome:
            try:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO prodotti (nome, materiale_trattamento, costo_interno, prezzo_vendita)
                            VALUES (%s, %s, %s, %s)
                        """, (nome, materiale, costo_int, prezzo_ven))
                        conn.commit()
                st.success(f"Prodotto '{nome}' salvato con successo!")
                st.rerun()
            except Exception as e:
                st.error(f"Errore nel salvataggio: {e}")

    with get_connection() as conn:
        df_prod = pd.read_sql("SELECT * FROM prodotti", conn)
    st.dataframe(df_prod, use_container_width=True)

# ---------------------------------------------------------
# TAB 3: AZIENDE
# ---------------------------------------------------------
with tab_aziende:
    st.header("Anagrafica Aziende / Clienti")
    
    with st.form("nuova_azienda"):
        ragione_sociale = st.text_input("Ragione Sociale")
        piva = st.text_input("Partita IVA")
        email = st.text_input("Email di Contatto")
        submit_az = st.form_submit_button("Aggiungi Azienda")
        
        if submit_az and ragione_sociale:
            try:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO aziende (ragione_sociale, piva, email)
                            VALUES (%s, %s, %s)
                        """, (ragione_sociale, piva, email))
                        conn.commit()
                st.success(f"Azienda '{ragione_sociale}' aggiunta!")
                st.rerun()
            except Exception as e:
                st.error(f"Errore durante l'inserimento: {e}")

    with get_connection() as conn:
        df_az = pd.read_sql("SELECT * FROM aziende", conn)
    st.dataframe(df_az, use_container_width=True)

# ---------------------------------------------------------
# TAB 4: ASSISTENTE GEMINI AI
# ---------------------------------------------------------
with tab_ai:
    st.header("🤖 Assistente AI per l'Analisi Dati")
    st.caption("Fai domande sul tuo database in linguaggio naturale (es. 'Mostrami i preventivi con importo maggiore di 500€').")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Come posso aiutarti oggi?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if client:
            try:
                # Esempio chiamata Gemini con SDK google-genai
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction="Sei un assistente per un gestionale aziendale. Rispondi in modo professionale e conciso."
                    )
                )
                
                with st.chat_message("assistant"):
                    st.markdown(response.text)
                
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Errore durante la generazione della risposta: {e}")
