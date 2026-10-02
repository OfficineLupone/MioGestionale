import streamlit as st
import sqlite3
import pandas as pd
from google import genai
from google.genai import types
import database

# Inizializzazione DB e pagina
database.init_db()
st.set_page_config(page_title="Gestionale IA Conversazionale", layout="wide")

def get_connection():
    return sqlite3.connect('gestionale.db')

api_key = st.secrets.get("GEMINI_API_KEY", "")

# --- FUNZIONI DI MODIFICA AUTOMATICA ESEGUITE DALL'IA ---
def aggiungi_settore_ai(nome_settore: str) -> str:
    """Aggiunge un nuovo settore di lavorazione al gestionale.
    
    Args:
        nome_settore: Il nome del nuovo settore da aggiungere.
    """
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
    """Rinomina un settore di lavorazione esistente nel gestionale.
    
    Args:
        vecchio_nome: Il nome attuale del settore da modificare.
        nuovo_nome: Il nuovo nome da assegnare al settore.
    """
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

def aggiorna_prodotto_ai(nome_prodotto: str, ore: float, costo: float, prezzo: float) -> str:
    """Crea o aggiorna un prodotto con ore di lavorazione, costo interno e prezzo di vendita.
    
    Args:
        nome_prodotto: Nome del prodotto o servizio.
        ore: Ore stimate di lavorazione.
        costo: Costo interno per l'azienda in Euro.
        prezzo: Prezzo di vendita al cliente in Euro.
    """
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

# Mappa per l'esecuzione manuale del tool
tools_map = {
    "aggiungi_settore_ai": aggiungi_settore_ai,
    "rinomina_settore_ai": rinomina_settore_ai,
    "aggiorna_prodotto_ai": aggiorna_prodotto_ai
}

# Lista di funzioni per Gemini
tools_list = [aggiungi_settore_ai, rinomina_settore_ai, aggiorna_prodotto_ai]

# --- MENU E INTERFACCIA ---
st.sidebar.title("🤖 Gestionale AI")
menu = st.sidebar.radio("Navigazione", ["💬 Assistente Chat IA", "📦 Catalogo & Settori", "📄 Preventivi", "🛠️ Consuntivo Ore", "📊 Report"])

# 1. CHAT PER MODIFICHE AUTOMATICHE
if menu == "💬 Assistente Chat IA":
    st.header("💬 Modifica il Gestionale Scrivendo all'IA")
    st.info("Scrivi ad esempio: 'Aggiungi il settore Verniciatura', 'Rinomina il settore Lavorazione in Taglio Laser', oppure 'Crea il prodotto Taglio Laser con 5 ore, costo 20 e prezzo 50'")
    
    comando = st.text_input("Scrivi qui il comando:")
    
    if st.button("Invia Comando") and comando:
        if api_key:
            try:
                client = genai.Client(api_key=api_key)
                with st.spinner("L'IA sta elaborando la richiesta..."):
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=comando,
                        config=types.GenerateContentConfig(
                            tools=tools_list,
                            temperature=0
                        )
                    )
                    
                    # Gestione dell'esecuzione della funzione
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
            except Exception as err:
                st.error(f"Errore durante l'esecuzione del comando: {err}")
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
