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
    page_title="Officine Lupone",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. STILE CSS PERSONALIZZATO ---
st.markdown("""
    <style>
    .main {
        background-color: #f8fafc;
    }
    h1 {
        color: #0f172a;
        font-weight: 700 !important;
        font-size: 2rem !important;
        margin-bottom: 0.5rem !important;
    }
    h2, h3 {
        color: #1e293b;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    [data-testid="stPills"] button {
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 600 !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    </style>
""", unsafe_allow_html=True)

def get_connection():
    return sqlite3.connect('gestionale.db')

api_key = st.secrets.get("GEMINI_API_KEY", "")

# --- FUNZIONI BACKEND PER IL DATABASE ---
def aggiungi_settore_db(nome_settore: str) -> str:
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO settori (nome) VALUES (?)", (nome_settore.strip(),))
        conn.commit()
        conn.close()
        return f"✅ Settore '{nome_settore}' aggiunto!"
    except Exception as e:
        return f"Errore: {e}"

def rinomina_settore_db(vecchio_nome: str, nuovo_nome: str) -> str:
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE settori SET nome = ? WHERE nome = ?", (nuovo_nome.strip(), vecchio_nome))
        conn.commit()
        conn.close()
        return f"✅ Settore '{vecchio_nome}' rinominato in '{nuovo_nome}'!"
    except Exception as e:
        return f"Errore: {e}"

def elimina_settore_db(nome_settore: str) -> str:
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM settori WHERE nome = ?", (nome_settore,))
        conn.commit()
        conn.close()
        return f"🗑️ Settore '{nome_settore}' eliminato!"
    except Exception as e:
        return f"Errore: {e}"

def reset_settori_ai(nuovi_settori: list[str]) -> str:
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM settori")
        c.execute("DELETE FROM sqlite_sequence WHERE name='settori'")
        for settore in nuovi_settori:
            c.execute("INSERT INTO settori (nome) VALUES (?)", (settore.strip(),))
        conn.commit()
        conn.close()
        return f"✅ Settori resettati! Nuovo ordine: {', '.join(nuovi_settori)}"
    except Exception as e:
        return f"Errore: {e}"

def aggiorna_prodotto_db(nome_prodotto: str, ore: float, costo: float, prezzo: float) -> str:
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
        """, (nome_prodotto.strip(), ore, costo, prezzo))
        conn.commit()
        conn.close()
        return f"✅ Prodotto '{nome_prodotto}' salvato/aggiornato!"
    except Exception as e:
        return f"Errore: {e}"

def elimina_prodotto_db(nome_prodotto: str) -> str:
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM prodotti WHERE nome = ?", (nome_prodotto,))
        conn.commit()
        conn.close()
        return f"🗑️ Prodotto '{nome_prodotto}' eliminato!"
    except Exception as e:
        return f"Errore: {e}"

# Mappature per l'IA
tools_map = {
    "aggiungi_settore_ai": aggiungi_settore_db,
    "rinomina_settore_ai": rinomina_settore_db,
    "reset_settori_ai": reset_settori_ai,
    "aggiorna_prodotto_ai": aggiorna_prodotto_db
}

tools_list = [aggiungi_settore_db, rinomina_settore_db, reset_settori_ai, aggiorna_prodotto_db]

# --- BARRA LATERALE E MENU ---
with st.sidebar:
    st.title("⚙️ Officine Lupone")
    st.caption("Sistema Gestionale Conversazionale")
    st.divider()
    
    st.write("**Navigazione**")
    menu = st.pills(
        label="Scegli la sezione:",
        options=["💬 Assistente IA", "📦 Catalogo & Settori", "📄 Preventivi", "🛠️ Consuntivo Ore", "📊 Report"],
        default="📦 Catalogo & Settori",
        label_visibility="collapsed"
    )
    st.divider()
    st.caption("Versione 2.5 • Enterprise UI")

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
    
    if st.button("🚀 Esegui Comando", type="primary") and comando:
        if api_key:
            client = genai.Client(api_key=api_key)
            response = None
            # Lista estesa di modelli per evitare l'errore 429 di quota esaurita
            modelli_da_provare = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.5-pro", "gemini-flash-latest"]
            
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
                        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "503" in str(e) or "UNAVAILABLE" in str(e):
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
                            st.rerun()
                elif response.text:
                    st.success(response.text)
                else:
                    st.info("Operazione completata con successo.")
            else:
                st.error("Quota limite dell'API temporaneamente raggiunta su tutti i modelli. Riprova più tardi o usa i pulsanti manuali.")
        else:
            st.error("Manca la chiave GEMINI_API_KEY nei Secrets di Streamlit!")

# --- 2. CATALOGO E SETTORI ---
elif menu == "📦 Catalogo & Settori":
    st.title("📦 Catalogo & Settori Lavorazione")
    st.write("Gestisci settori e prodotti sia manualmente con i pulsanti sia tramite l'Assistente IA.")
    
    conn = get_connection()
    df_settori = pd.read_sql_query("SELECT id AS 'ID', nome AS 'Nome Settore' FROM settori", conn)
    df_prodotti = pd.read_sql_query("SELECT id AS 'ID', nome AS 'Prodotto', ore_lavorazione AS 'Ore Stimate', costo_interno AS 'Costo (€)', prezzo_vendita AS 'Prezzo (€)' FROM prodotti", conn)
    conn.close()

    # KPI In Alto
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
    
    # --- SEZIONE SETTORI ---
    with col1:
        with st.container(border=True):
            st.subheader("🏬 Settori Lavorazione")
            
            c_btn1, c_btn2 = st.columns(2)
            
            with c_btn1:
                with st.popover("➕ Aggiungi Settore", use_container_width=True):
                    st.write("**Nuovo Settore**")
                    nuovo_set = st.text_input("Nome Settore:")
                    if st.button("Salva Settore", type="primary"):
                        if nuovo_set:
                            res = aggiungi_settore_db(nuovo_set)
                            st.success(res)
                            st.rerun()

            with c_btn2:
                with st.popover("✏️ Modifica / 🗑️ Elimina", use_container_width=True):
                    st.write("**Gestione Settori**")
                    if not df_settori.empty:
                        settore_sel = st.selectbox("Seleziona Settore:", df_settori['Nome Settore'].tolist())
                        nuovo_nome_set = st.text_input("Rinomina in:", value=settore_sel)
                        
                        col_mod, col_del = st.columns(2)
                        with col_mod:
                            if st.button("Rinomina", type="primary"):
                                res = rinomina_settore_db(settore_sel, nuovo_nome_set)
                                st.success(res)
                                st.rerun()
                        with col_del:
                            if st.button("Elimina", type="secondary"):
                                res = elimina_settore_db(settore_sel)
                                st.success(res)
                                st.rerun()
                    else:
                        st.info("Nessun settore presente.")

            # Tabella Settori
            st.dataframe(df_settori, use_container_width=True, hide_index=True)

    # --- SEZIONE PRODOTTI ---
    with col2:
        with st.container(border=True):
            st.subheader("📋 Catalogo Prodotti e Listino")
            
            cp_btn1, cp_btn2 = st.columns(2)
            
            with cp_btn1:
                with st.popover("➕ Aggiungi / Aggiorna Prodotto", use_container_width=True):
                    st.write("**Dettagli Prodotto**")
                    p_nome = st.text_input("Nome Prodotto:")
                    p_ore = st.number_input("Ore Stimate:", min_value=0.0, step=0.5)
                    p_costo = st.number_input("Costo Interno (€):", min_value=0.0, step=10.0)
                    p_prezzo = st.number_input("Prezzo Vendita (€):", min_value=0.0, step=10.0)
                    if st.button("Salva Prodotto", type="primary"):
                        if p_nome:
                            res = aggiorna_prodotto_db(p_nome, p_ore, p_costo, p_prezzo)
                            st.success(res)
                            st.rerun()

            with cp_btn2:
                with st.popover("🗑️ Elimina Prodotto", use_container_width=True):
                    st.write("**Elimina dal Catalogo**")
                    if not df_prodotti.empty:
                        prod_sel = st.selectbox("Seleziona Prodotto:", df_prodotti['Prodotto'].tolist())
                        if st.button("Conferma Eliminazione", type="secondary"):
                            res = elimina_prodotto_db(prod_sel)
                            st.success(res)
                            st.rerun()
                    else:
                        st.info("Nessun prodotto presente.")

            # Tabella Prodotti
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
        if st.button("Salva Registro Ore", type="primary"):
            st.success(f"Registrate {ore_eff} ore per il settore {settore_sel}")

# --- 5. REPORT ---
elif menu == "📊 Report":
    st.title("📊 Report e Analytics")
    st.info("Funzionalità in fase di sviluppo.")
