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
    page_title="FSL GESTIONALE - Dashboard",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS PERSONALIZZATO ISO-DESIGN (STILE DA SCHERMATA) ---
st.markdown("""
    <style>
    /* Sfondo generale grigio chiarissimo/bianco caldo */
    .stApp {
        background-color: #f6f8f7;
    }
    
    /* Nascondi elementi di default Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Header Superiore */
    .top-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem 1rem;
        background-color: #f6f8f7;
        margin-bottom: 0.5rem;
    }
    .brand-title {
        font-weight: 800;
        font-size: 1.15rem;
        color: #0d1b1e;
        letter-spacing: -0.5px;
    }
    .brand-sub {
        font-size: 0.78rem;
        color: #64748b;
        margin-top: -2px;
    }
    
    /* Cards KPI / Metriche stile SaaS */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    div[data-testid="stMetricLabel"] {
        color: #64748b !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
    }
    div[data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
    }
    
    /* Banner Informativo Beige / Avviso */
    .alert-banner {
        background-color: #fdf8eb;
        border: 1px solid #f2e3c6;
        border-radius: 8px;
        padding: 0.85rem 1.2rem;
        color: #78350f;
        font-size: 0.88rem;
        margin-bottom: 1.2rem;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    /* Pulsanti principali (Verde Scuro scuro tipo la foto) */
    .stButton>button[kind="primary"] {
        background-color: #0e3d2f !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 0.5rem 1.2rem !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: #145240 !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15) !important;
    }
    
    /* Customizzazione Tabs di navigazione */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1.5rem;
        background-color: transparent;
        border-bottom: 2px solid #e2e8f0;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        white-space: pre;
        background-color: transparent;
        border: none;
        color: #64748b;
        font-weight: 500;
        font-size: 0.9rem;
        padding: 0 0.2rem;
    }
    .stTabs [aria-selected="true"] {
        color: #0d1b1e !important;
        font-weight: 700 !important;
        border-bottom: 3px solid #0e3d2f !important;
    }
    
    /* Tabelle stilizzate */
    .stDataFrame {
        background-color: #ffffff;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }
    </style>
""", unsafe_allow_html=True)

def get_connection():
    return sqlite3.connect('gestionale.db')

api_key = st.secrets.get("GEMINI_API_KEY", "")

# --- FUNZIONI BACKEND ---
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
            if settore.strip():
                c.execute("INSERT INTO settori (nome) VALUES (?)", (settore.strip(),))
        conn.commit()
        conn.close()
        return f"✅ Settori resettati: {', '.join(nuovi_settori)}"
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
        return f"✅ Prodotto '{nome_prodotto}' salvato!"
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

tools_map = {
    "aggiungi_settore_ai": aggiungi_settore_db,
    "rinomina_settore_ai": rinomina_settore_db,
    "reset_settori_ai": reset_settori_ai,
    "aggiorna_prodotto_ai": aggiorna_prodotto_db
}
tools_list = [aggiungi_settore_db, rinomina_settore_db, reset_settori_ai, aggiorna_prodotto_db]

# --- 3. HEADER SUPERIORE ---
h_left, h_right = st.columns([3, 1])
with h_left:
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 12px;">
            <div style="background-color: #0e3d2f; color: white; padding: 8px 12px; border-radius: 8px; font-weight: bold;">🛡️</div>
            <div>
                <div class="brand-title">GESTIONALE ENTERPRISE</div>
                <div class="brand-sub">Sistema Integrato AI • Versione 2.5</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

st.write("")

# --- 4. MENU A SCHEDE SUPEROIRE (NAVIGATION TABS) ---
tab_panoramica, tab_assistente, tab_preventivi, tab_lavori, tab_report = st.tabs([
    "Panoramica & Catalogo", 
    "💬 Assistente IA", 
    "📄 Preventivi", 
    "🛠️ Consuntivo Ore", 
    "📊 Report"
])

# --- TAB 1: PANORAMICA & CATALOGO ---
with tab_panoramica:
    conn = get_connection()
    df_settori = pd.read_sql_query("SELECT id AS 'ID', nome AS 'Nome Settore' FROM settori", conn)
    df_prodotti = pd.read_sql_query("SELECT id AS 'ID', nome AS 'Prodotto', ore_lavorazione AS 'Ore Stimate', costo_interno AS 'Costo (€)', prezzo_vendita AS 'Prezzo (€)' FROM prodotti", conn)
    conn.close()

    # Titolo di Sezione e Pulsante d'Azione rapida in alto
    t_col1, t_col2 = st.columns([3, 1])
    with t_col1:
        st.markdown("<h2 style='margin:0;'>Panoramica Generale</h2>", unsafe_allow_html=True)
    with t_col2:
        with st.popover("+ Nuovo Settore / Prodotto", use_container_width=True):
            st.write("**Azione Rapida**")
            tipo = st.radio("Cosa vuoi aggiungere?", ["Settore", "Prodotto"])
            if tipo == "Settore":
                n_s = st.text_input("Nome Settore:")
                if st.button("Salva Settore", type="primary"):
                    if n_s:
                        aggiungi_settore_db(n_s)
                        st.rerun()
            else:
                p_n = st.text_input("Nome Prodotto:")
                p_o = st.number_input("Ore:", min_value=0.0)
                p_c = st.number_input("Costo (€):", min_value=0.0)
                p_p = st.number_input("Prezzo (€):", min_value=0.0)
                if st.button("Salva Prodotto", type="primary"):
                    if p_n:
                        aggiorna_prodotto_db(p_n, p_o, p_c, p_p)
                        st.rerun()

    st.write("")

    # SCHEDE KPI
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Settori Registrati", len(df_settori))
    with k2:
        st.metric("Prodotti a Catalogo", len(df_prodotti))
    with k3:
        tot_ore = df_prodotti['Ore Stimate'].sum() if not df_prodotti.empty else 0
        st.metric("Ore Totali Stimate", f"{tot_ore:.1f} h")
    with k4:
        margine = (df_prodotti['Prezzo (€)'] - df_prodotti['Costo (€)']).mean() if not df_prodotti.empty else 0
        st.metric("Margine Medio / Prod.", f"€ {margine:,.2f}")

    st.write("")

    # BANNER DI AVVISO STILE INTERFACCIA
    if df_settori.empty:
        st.markdown("""
            <div class="alert-banner">
                ⚠️ <b>Attenzione:</b> Non ci sono settori configurati nel database. Aggiungine uno usando il pulsante in alto o chiedi all'Assistente IA.
            </div>
        """, unsafe_allow_html=True)

    # TABELLE CATALOGO E SETTORI
    col_left, col_right = st.columns([1, 2])

    with col_left:
        with st.container():
            st.markdown("### 🏬 Settori Lavorazione")
            
            s_btn1, s_btn2 = st.columns(2)
            with s_btn1:
                with st.popover("✏️ Rinomina", use_container_width=True):
                    if not df_settori.empty:
                        s_sel = st.selectbox("Seleziona:", df_settori['Nome Settore'].tolist(), key="ren_s")
                        s_new = st.text_input("Nuovo nome:", value=s_sel, key="ren_txt")
                        if st.button("Conferma", type="primary", key="btn_ren"):
                            rinomina_settore_db(s_sel, s_new)
                            st.rerun()
            with s_btn2:
                with st.popover("🗑️ Elimina", use_container_width=True):
                    if not df_settori.empty:
                        s_del = st.selectbox("Elimina:", df_settori['Nome Settore'].tolist(), key="del_s")
                        if st.button("Conferma Elimina", type="secondary", key="btn_del"):
                            elimina_settore_db(s_del)
                            st.rerun()

            st.dataframe(df_settori, use_container_width=True, hide_index=True)

    with col_right:
        with st.container():
            st.markdown("### 📋 Catalogo Prodotti e Listino")
            
            p_btn1, p_btn2 = st.columns([1, 1])
            with p_btn2:
                with st.popover("🗑️ Elimina Prodotto", use_container_width=True):
                    if not df_prodotti.empty:
                        pr_del = st.selectbox("Elimina Prodotto:", df_prodotti['Prodotto'].tolist(), key="del_p")
                        if st.button("Conferma Eliminazione", type="secondary", key="btn_del_p"):
                            elimina_prodotto_db(pr_del)
                            st.rerun()

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

# --- TAB 2: ASSISTENTE IA ---
with tab_assistente:
    st.markdown("## 💬 Assistente Virtuale")
    st.caption("Esegui azioni sul gestionale scrivendo in linguaggio naturale.")
    
    cmd = st.text_input("Impartisci un comando all'IA:", placeholder="Es. Reset settori con Tornitura, Fresatura e Assemblaggio...")
    if st.button("🚀 Esegui Comando", type="primary") and cmd:
        if api_key:
            client = genai.Client(api_key=api_key)
            response = None
            modelli_validi = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
            
            with st.spinner("Elaborazione in corso..."):
                for mod in modelli_validi:
                    try:
                        response = client.models.generate_content(
                            model=mod,
                            contents=cmd,
                            config=types.GenerateContentConfig(tools=tools_list, temperature=0)
                        )
                        break
                    except Exception:
                        continue
            
            if response:
                if hasattr(response, 'function_calls') and response.function_calls:
                    for call in response.function_calls:
                        if call.name in tools_map:
                            res = tools_map[call.name](**call.args)
                            st.success(res)
                            st.rerun()
                elif response.text:
                    st.success(response.text)
            else:
                st.error("Servizio temporaneamente non disponibile. Riprova tra poco.")
        else:
            st.error("Configura la chiave GEMINI_API_KEY nei secrets!")

# --- TAB 3, 4, 5: ALTRE SEZIONI ---
with tab_preventivi:
    st.markdown("## 📄 Gestione Preventivi")
    st.info("Modulo preventivi in aggiornamento.")

with tab_lavori:
    st.markdown("## 🛠️ Consuntivo Ore Lavorate")
    st.info("Modulo registrazione ore in aggiornamento.")

with tab_report:
    st.markdown("## 📊 Report & Analytics")
    st.info("Modulo reportistica in aggiornamento.")
