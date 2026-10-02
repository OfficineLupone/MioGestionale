import streamlit as st
import sqlite3
import pandas as pd
from google import genai
from google.genai import types
import database

# --- 1. CONFIGURAZIONE PAGINA ---
database.init_db()
st.set_page_config(
    page_title="OFFICINE LUPONE - Dashboard",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS PERSONALIZZATO ISO-DESIGN ---
st.markdown("""
    <style>
    .stApp {
        background-color: #f6f8f7;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
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
    
    .alert-banner {
        background-color: #fdf8eb;
        border: 1px solid #f2e3c6;
        border-radius: 8px;
        padding: 0.85rem 1.2rem;
        color: #78350f;
        font-size: 0.88rem;
        margin-bottom: 1.2rem;
    }
    
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

# --- FUNZIONI BACKEND SETTORI & OPERATORI ---
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

def aggiungi_operatore_db(nome_operatore: str, settore_id: int) -> str:
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO operatori (nome, settore_id) VALUES (?, ?)", (nome_operatore.strip(), settore_id))
        conn.commit()
        conn.close()
        return f"✅ Operatore '{nome_operatore}' aggiunto!"
    except Exception as e:
        return f"Errore: {e}"

def elimina_operatore_db(operatore_id: int) -> str:
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM operatori WHERE id = ?", (operatore_id,))
        conn.commit()
        conn.close()
        return f"🗑️ Operatore rimosso!"
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

# LETTURA DATI DB
conn = get_connection()
df_settori = pd.read_sql_query("SELECT id AS 'ID', nome AS 'Nome Settore' FROM settori", conn)
df_operatori = pd.read_sql_query("""
    SELECT o.id AS 'ID', o.nome AS 'Nome Operatore', s.nome AS 'Settore', o.settore_id 
    FROM operatori o 
    JOIN settori s ON o.settore_id = s.id
""", conn)
df_prodotti = pd.read_sql_query("SELECT id AS 'ID', nome AS 'Prodotto', ore_lavorazione AS 'Ore Stimate', costo_interno AS 'Costo (€)', prezzo_vendita AS 'Prezzo (€)' FROM prodotti", conn)
conn.close()

# --- 4. MENU A SCHEDE SEPARATE ---
tab_panoramica, tab_settori, tab_prodotti, tab_preventivi, tab_report, tab_assistente = st.tabs([
    "Panoramica", 
    "Settori Produttivi", 
    "Catalogo Prodotti", 
    "Preventivi", 
    "Report",
    "💬 Assistente IA"
])

# --- 1. PANORAMICA ---
with tab_panoramica:
    st.markdown("## Panoramica Generale")
    st.write("")

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Settori Registrati", len(df_settori))
    with k2:
        st.metric("Operatori Totali", len(df_operatori))
    with k3:
        st.metric("Prodotti a Catalogo", len(df_prodotti))
    with k4:
        margine = (df_prodotti['Prezzo (€)'] - df_prodotti['Costo (€)']).mean() if not df_prodotti.empty else 0
        st.metric("Margine Medio / Prod.", f"€ {margine:,.2f}")

    st.write("")

    if df_settori.empty:
        st.markdown("""
            <div class="alert-banner">
                ⚠️ <b>Nessun settore registrato:</b> Vai nella scheda <b>Settori Produttivi</b> per aggiungerne uno o usa l'Assistente IA.
            </div>
        """, unsafe_allow_html=True)

    c_left, c_right = st.columns(2)
    with c_left:
        st.markdown("### 🏬 Ultimi Settori")
        st.dataframe(df_settori, use_container_width=True, hide_index=True)
    with c_right:
        st.markdown("### 👷‍♂️ Operatori per Settore")
        if not df_operatori.empty:
            st.dataframe(df_operatori[['Nome Operatore', 'Settore']], use_container_width=True, hide_index=True)
        else:
            st.info("Nessun operatore assegnato.")

# --- 2. SETTORI PRODUTTIVI ---
with tab_settori:
    st.markdown("## 🏬 Gestione Settori & Operatori")
    st.write("Configura i settori di lavorazione e assegna gli operatori qualificati.")
    
    # PULSANTI DI GESTIONE SETTORI
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    
    with col_s1:
        with st.popover("➕ Nuovo Settore", use_container_width=True):
            st.write("**Aggiungi Settore**")
            nuovo_s = st.text_input("Nome Settore:", key="set_add_input")
            if st.button("Salva Settore", type="primary", key="btn_add_s"):
                if nuovo_s:
                    aggiungi_settore_db(nuovo_s)
                    st.rerun()

    with col_s2:
        with st.popover("✏️ Rinomina Settore", use_container_width=True):
            if not df_settori.empty:
                s_sel = st.selectbox("Seleziona da rinominare:", df_settori['Nome Settore'].tolist(), key="set_ren_sel")
                s_new = st.text_input("Nuovo nome:", value=s_sel, key="set_ren_txt")
                if st.button("Conferma Rinomina", type="primary", key="btn_ren_s"):
                    rinomina_settore_db(s_sel, s_new)
                    st.rerun()
            else:
                st.info("Nessun settore presente.")

    with col_s3:
        with st.popover("🗑️️ Elimina Settore", use_container_width=True):
            if not df_settori.empty:
                s_del = st.selectbox("Seleziona da eliminare:", df_settori['Nome Settore'].tolist(), key="set_del_sel")
                if st.button("Conferma Eliminazione", type="secondary", key="btn_del_s"):
                    elimina_settore_db(s_del)
                    st.rerun()
            else:
                st.info("Nessun settore presente.")

    with col_s4:
        with st.popover("👷‍♂️ Aggiungi Operatore", use_container_width=True):
            st.write("**Nuovo Operatore**")
            if not df_settori.empty:
                set_target = st.selectbox("Assegna al Settore:", df_settori['Nome Settore'].tolist(), key="op_set_target")
                op_nome = st.text_input("Nome e Cognome Operatore:", key="op_name_input")
                if st.button("Salva Operatore", type="primary", key="btn_add_op"):
                    if op_nome:
                        s_id = df_settori[df_settori['Nome Settore'] == set_target]['ID'].values[0]
                        aggiungi_operatore_db(op_nome, int(s_id))
                        st.rerun()
            else:
                st.info("Crea prima almeno un settore.")

    st.write("")
    
    # VISUALIZZAZIONE SCHEDE SETTORI CON OPERATORI
    if not df_settori.empty:
        col_m1, col_m2 = st.columns(2)
        for i, row in df_settori.iterrows():
            target_col = col_m1 if i % 2 == 0 else col_m2
            with target_col:
                with st.container(border=True):
                    st.markdown(f"### 🏭 {row['Nome Settore']}")
                    
                    # Filtra gli operatori di questo settore
                    ops = df_operatori[df_operatori['settore_id'] == row['ID']] if not df_operatori.empty else pd.DataFrame()
                    
                    if not ops.empty:
                        st.write("**Operatori Assegnati:**")
                        for _, op_row in ops.iterrows():
                            c_op1, c_op2 = st.columns([4, 1])
                            with c_op1:
                                st.write(f"• 👤 **{op_row['Nome Operatore']}**")
                            with c_op2:
                                if st.button("🗑️", key=f"del_op_{op_row['ID']}", help="Rimuovi operatore"):
                                    elimina_operatore_db(op_row['ID'])
                                    st.rerun()
                    else:
                        st.caption("Nessun operatore inserito per questo settore.")
    else:
        st.info("Nessun settore disponibile.")

# --- 3. CATALOGO PRODOTTI ---
with tab_prodotti:
    st.markdown("## 📋 Catalogo Prodotti e Listino")
    st.write("Gestisci i prodotti a listino con relativi prezzi e stime orarie.")

    cp1, cp2 = st.columns(2)
    with cp1:
        with st.popover("➕ Aggiungi / Modifica Prodotto", use_container_width=True):
            st.write("**Dettagli Prodotto**")
            p_n = st.text_input("Nome Prodotto:", key="p_name_inp")
            p_o = st.number_input("Ore Lavorazione:", min_value=0.0, step=0.5, key="p_ore_inp")
            p_c = st.number_input("Costo Interno (€):", min_value=0.0, step=10.0, key="p_cost_inp")
            p_p = st.number_input("Prezzo Vendita (€):", min_value=0.0, step=10.0, key="p_price_inp")
            if st.button("Salva Prodotto", type="primary", key="btn_save_p"):
                if p_n:
                    aggiorna_prodotto_db(p_n, p_o, p_c, p_p)
                    st.rerun()

    with cp2:
        with st.popover("🗑️ Elimina Prodotto", use_container_width=True):
            if not df_prodotti.empty:
                pr_del = st.selectbox("Seleziona Prodotto:", df_prodotti['Prodotto'].tolist(), key="p_del_sel")
                if st.button("Conferma Eliminazione", type="secondary", key="btn_del_p"):
                    elimina_prodotto_db(pr_del)
                    st.rerun()
            else:
                st.info("Nessun prodotto a catalogo.")

    st.write("")
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

# --- 4. PREVENTIVI ---
with tab_preventivi:
    st.markdown("## 📄 Generazione e Modulo Preventivi")
    st.info("Modulo gestione preventivi in fase di sviluppo.")

# --- 5. REPORT ---
with tab_report:
    st.markdown("## 📊 Report & Analytics")
    st.info("Modulo report e statistiche di produzione in fase di sviluppo.")

# --- 6. ASSISTENTE IA ---
with tab_assistente:
    st.markdown("## 💬 Assistente AI")
    st.caption("Fai richieste al gestionale scrivendo in linguaggio naturale.")
    
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
