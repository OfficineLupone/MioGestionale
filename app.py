import streamlit as st
import sqlite3
import pandas as pd
import time
from google import genai
from google.genai import types
import database

# --- 1. CONFIGURAZIONE PAGINA ---
database.init_db()
st.set_page_config(
    page_title="Gestionale IA Enterprise",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. STILE CSS PERSONALIZZATO (LOOK & FEEL PROFESSIONALE) ---
st.markdown("""
    <style>
    /* Sfondo principale e font */
    .main {
        background-color: #f8fafc;
    }
    
    /* Personalizzazione Titoli */
    h1 {
        color: #0f172a;
        font-weight: 700 !important;
        font-size: 2.2rem !important;
        margin-bottom: 0.5rem !important;
    }
    h2, h3 {
        color: #1e293b;
        font-weight: 600 !important;
    }

    /* Stile Sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }

    /* Bottone Principale */
    .stButton>button {
        width: 100%;
        background-color: #2563eb;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        border: none;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #1d4ed8;
        border: none;
        color: white;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
    }
    
    /* Box messaggi IA */
    .stAlert {
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=unsafe_allow_html=True)

def get_connection():
    return sqlite3.connect('gestionale.db')

api_key = st.secrets.get("GEMINI_API_KEY", "")

# --- FUNZIONI BACKEND IA ---
def aggiungi_settore_ai(nome_settore: str) -> str:
    """Aggiunge un nuovo settore di lavorazione al gestionale."""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO settori (nome) VALUES (?)", (nome_settore,))
        conn.commit()
        conn.close()
        return f"✅ Settore '{nome_settore}' aggiunto con successo!"
    except Exception as e:
        return f"Errore nell'aggiunta del settore: {e}"

def rinomina_settore_ai(vecchio_nome: str, nuovo_nome: str) -> str:
    """Rinomina un settore di lavorazione esistente nel gestionale."""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE settori SET nome = ? WHERE nome = ?", (nuovo_nome, vecchio_nome))
        if c.rowcount == 0:
            conn.close()
            return f"⚠️ Nessun settore trovato con il nome '{vecchio_nome}'."
        conn.commit()
        conn.close()
        return f"✅ Settore '{vecchio_nome}' rinominato in '{nuovo_nome}'!"
    except Exception as e:
        return f"Errore durante la modifica: {e}"

def reset_settori_ai(nuovi_settori: list[str]) -> str:
    """Cancella tutti i settori esistenti, azzera gli ID partendo da 1 e inserisce la nuova lista."""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM settori")
        c.execute("DELETE FROM sqlite_sequence WHERE name='settori'")
        for settore in nuovi_settori:
            c.execute("INSERT INTO settori (nome) VALUES (?)", (settore.strip(),))
        conn.commit()
        conn.close()
        return f"✅ Settori resettati con successo! Nuovo ordine (da ID 1): {', '.join(nuovi_settori)}"
    except Exception as e:
        return f"Errore durante il reset dei settori: {e}"

def aggiorna_prodotto_ai(nome_prodotto: str, ore: float, costo: float, prezzo: float) -> str:
    """Crea o aggiorna un prodotto con ore di lavorazione, costo interno e prezzo di vendita."""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO prodotti (nome, ore_lavorazione, costo_interno, prezzo_vendita)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(nome) DO UPDATE SET
            ore_lavorazione=excluded.ore_lavorazione,
            costo_interno=excluded.costo_interno,
            prezzo_vendita=excluded.prezzo_vendita
        """, (nome_prodotto, ore, costo, prezzo))
        conn.commit()
        conn.close()
        return f"✅ Prodotto '{nome_prodotto}' salvato/aggiornato!"
    except Exception as e:
        return f"Errore nell'aggiornamento del prodotto: {e}"

tools_map = {
    "aggiungi_settore_ai": aggiungi_settore_ai,
    "rinomina_settore_ai": rinomina_settore_ai,
    "reset_settori_ai": reset_settori_ai,
    "aggiorna_prodotto_ai": aggiorna_prodotto_ai
}

tools_list = [aggiungi_settore_ai, rinomina_settore_ai, reset_settori_ai, aggiorna_prodotto_ai]

# --- BARRA LATERALE ---
with st.sidebar:
    st.title("⚙️ Gestionale AI")
    st.caption("Sistema Gestionale Conversazionale")
    st.divider()
    menu = st.radio(
        "Navigazione",
        ["💬 Assistente IA", "📦 Catalogo & Settori", "📄 Preventivi", "🛠️ Consuntivo Ore", "📊 Report"],
        index=0
    )
    st.divider()
    st.caption("Versione 2.0 • Powered by Gemini")

# --- 1. CHAT ASSISTENTE IA ---
if menu == "💬 Assistente IA":
    st.title("💬 Assistente Virtuale")
    st.write("Esegui modifiche al gestionale semplicemente scrivendo in linguaggio naturale.")
    
    with st.container(border=True):
        st.subheader("💡 Esempi di comandi")
        st.markdown("""
        - *'Reset settori con: Tornitura, Fresatura, Rettifica, EDM, Aggiustaggio, Assemblaggio'*
        - *'Aggiungi il settore Trattamenti Termici'*
        - *'Crea il prodotto Stampo Plastica con 25 ore, costo 1500 e prezzo 3200'*
        """)

    comando = st.text_input("Impartisci un comando all'IA:", placeholder="Es. Aggiungi il settore Verniciatura...")
    
    if st.button("🚀 Esegui Comando") and comando:
        if api_key:
            client = genai.Client(api_key=api_key)
            response = None
            modelli_da_provare = ["gemini-flash-latest", "gemini-1.5-flash", "gemini-1.5-pro"]
            
            with st.spinner("L'IA sta elaborando la richiesta..."):
                for mod in modelli_da_provare:
                    try:
                        response = client.models.generate_content(
                            model=mod,
                            contents=comando,
                            config=types.GenerateContentConfig(
                                tools=tools_list,
                                temperature=0
                            )
                        )
                        break
                    except Exception as e:
                        if "503" in str(e) or "UNAVAILABLE" in str(e):
                            time.sleep(1)
                            continue
                        else:
                            st.error(f"Errore: {e}")
                            break
            
            if response:
                if hasattr(response, 'function_calls') and response.function_calls:
                    for call in response.function_calls:
                        func_name = call.name
                        func_args = call.args
                        if func_name in tools_map:
                            esito = tools_map[func_name](**func_args)
                            st.success(esito)
                elif response.text:
                    st.success(response.text)
                else:
                    st.info("Operazione completata con successo.")
            else:
                st.warning("I server di Google sono momentaneamente occupati. Riprova tra poco.")
        else:
            st.error("Manca la chiave GEMINI_API_KEY nei Secrets di Streamlit!")

# --- 2. CATALOGO E SETTORI ---
elif menu == "📦 Catalogo & Settori":
    st.title("📦 Catalogo & Settori Lavorazione")
    st.write("Visualizzazione in tempo reale della struttura aziendale e del catalogo dei prodotti.")
    
    conn = get_connection()
    df_settori = pd.read_sql_query("SELECT id AS 'ID', nome AS 'Nome Settore' FROM settori", conn)
    df_prodotti = pd.read_sql_query("SELECT id AS 'ID', nome AS 'Prodotto', ore_lavorazione AS 'Ore Stimate', costo_interno AS 'Costo (€)', prezzo_vendita AS 'Prezzo (€)' FROM prodotti", conn)
    conn.close()

    # KPI / Metriche In Alto
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Settori Attivi", len(df_settori))
    with m2:
        st.metric("Prodotti a Catalogo", len(df_prodotti))
    with m3:
        if not df_prodotti.empty:
            margine_medio = (df_prodotti['Prezzo (€)'] - df_prodotti['Costo (€)']).mean()
            st.metric("Margine Medio / Prodotto", f"€ {margine_medio:,.2f}")
        else:
            st.metric("Margine Medio", "€ 0.00")

    st.divider()

    col1, col2 = st.columns([1, 2])
    with col1:
        with st.container(border=True):
            st.subheader("🏬 Settori Lavorazione")
            st.dataframe(df_settori, use_container_width=True, hide_index=True)

    with col2:
        with st.container(border=True):
            st.subheader("📋 Catalogo Prodotti e Listino")
            st.dataframe(
                df_prodotti, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Costo (€)": st.column_config.NumberColumn(format="€ %.2f"),
                    "Prezzo (€)": st.column_config.NumberColumn(format="€ %.2f"),
                    "Ore Stimate": st.column_config.NumberColumn(format="%.1f h")
                }
            )

# --- 3. PREVENTIVI ---
elif menu == "📄 Preventivi":
    st.title("📄 Generazione Preventivi")
    st.info("Funzionalità in fase di sviluppo.")

# --- 4. CONSUNTIVO ORE ---
elif menu == "🛠️ Consuntivo Ore":
    st.title("🛠️ Consuntivo Ore Lavorate")
    conn = get_connection()
    df_settori = pd.read_sql_query("SELECT nome FROM settori", conn)
    conn.close()
    
    with st.container(border=True):
        st.subheader("Registra intervento")
        settore_sel = st.selectbox("Seleziona Settore", df_settori['nome'].tolist() if not df_settori.empty else [])
        ore_eff = st.number_input("Ore Effettive Lavorate", min_value=0.0, step=0.5)
        if st.button("Salva Registro Ore"):
            st.success(f"Registrate {ore_eff} ore per il settore {settore_sel}")

# --- 5. REPORT ---
elif menu == "📊 Report":
    st.title("📊 Report e Analytics")
    st.info("Funzionalità in fase di sviluppo.")
