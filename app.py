import streamlit as st
import sqlite3
import pandas as pd
from google import genai
from google.genai import types
import database

database.init_db()
st.set_page_config(page_title="Gestionale IA Conversazionale", layout="wide")

def get_connection():
    return sqlite3.connect('gestionale.db')

api_key = st.secrets.get("GEMINI_API_KEY", "")

# --- FUNZIONI DI MODIFICA AUTOMATICA ESEGUITE DALL'IA ---
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

def aggiorna_prodotto_ai(nome_prodotto: str, ore: float, costo: float, prezzo: float) -> str:
    """Crea o aggiorna un prodotto con ore, costo interno e prezzo di vendita."""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO prodotti (nome, ore_lavorazione, costo_interno, prezzo_vendita)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(nome) DO UPDATE SET
            ore_lavorazione=excluded.ore_lavorazione, costo_interno=excluded.costo_interno, prezzo_vendita=excluded.prezzo_vendita
        """, (nome_prodotto, ore, costo, prezzo))
        conn.commit()
        conn.close()
        return f"✅ Prodotto '{nome_prodotto}' salvato/aggiornato!"
    except Exception as e:
        return f"Errore nell'aggiornamento del prodotto: {e}"

tools_list = [aggiungi_settore_ai, aggiorna_prodotto_ai]

# --- MENU E INTERFACCIA ---
st.sidebar.title("🤖 Gestionale AI")
menu = st.sidebar.radio("Navigazione", ["💬 Assistente Chat IA", "📦 Catalogo & Settori", "📄 Preventivi", "🛠️ Consuntivo Ore", "📊 Report"])

# 1. CHAT PER MODIFICHE AUTOMATICHE
if menu == "💬 Assistente Chat IA":
    st.header("💬 Modifica il Gestionale Scrivendo all'IA")
    st.info("Scrivi ad esempio: 'Aggiungi il settore Verniciatura' oppure 'Crea il prodotto Taglio Laser con 5 ore, costo 20 e prezzo 50'")
    comando = st.text_input("Scrivi qui il comando:")
    if st.button("Invia Comando") and comando:
        if api_key:
            client = genai.Client(api_key=api_key)
            with st.spinner("L'IA sta modificando il database..."):
                response = client.models.generate_content(
                    model="gemini-2.5-flash", contents=comando,
                    config=types.GenerateContentConfig(tools=tools_list, temperature=0)
                )
                st.success(response.text)
        else:
            st.error("Manca la chiave GEMINI_API_KEY nei Secrets di Streamlit!")

# 2. CATALOGO E SETTORI
elif menu == "📦 Catalogo & Settori":
    st.header("⚙️ Settori e Prodotti Registrati")
    conn = get_connection()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Settori attivi")
        st.dataframe(pd.read_sql_query("SELECT * FROM settori", conn), use_container_width=True)
    with c2:
        st.subheader("Catalogo Prodotti")
        st.dataframe(pd.read_sql_query("SELECT * FROM prodotti", conn), use_container_width=True)
    conn.close()
    
    # Aggiungi questa nuova funzione nel codice:
def rinomina_settore_ai(vecchio_nome: str, nuovo_nome: str) -> str:
    """Rinomina un settore esistente nel gestionale."""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE settori SET nome = ? WHERE nome = ?", (nuovo_nome, vecchio_nome))
        if c.rowcount == 0:
            conn.close()
            return f"⚠️ Nessun settore trovato con il nome '{vecchio_nome}'."
        conn.commit()
        conn.close()
        return f"✅ Settore '{vecchio_nome}' rinominato con successo in '{nuovo_nome}'!"
    except Exception as e:
        return f"Errore durante la modifica: {e}"

# Aggiorna la lista dei tool messi a disposizione dell'IA:
tools_list = [aggiungi_settore_ai, rinomina_settore_ai, aggiorna_prodotto_ai]

# 3. PREVENTIVI
elif menu == "📄 Preventivi":
    st.header("📄 Generazione Preventivi")
    st.write("Genera e scarica qui le tue offerte commerciali.")

# 4. CONSUNTIVO ORE
elif menu == "🛠️ Consuntivo Ore":
    st.header("🛠️ Registrazione Ore Lavorate per Settore")
    conn = get_connection()
    df_settori = pd.read_sql_query("SELECT nome FROM settori", conn)
    conn.close()
    st.selectbox("Seleziona Settore", df_settori['nome'].tolist() if not df_settori.empty else [])
    st.number_input("Ore Effettive", min_value=0.0, step=0.5)
    st.button("Salva Consuntivo")

# 5. REPORT
elif menu == "📊 Report":
    st.header("📊 Analisi Profitti")
    st.write("Grafici di scostamento ore stimate vs ore reali.")
