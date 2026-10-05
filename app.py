import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import database

# --- 1. CONFIGURAZIONE PAGINA E DB ---
st.set_page_config(
    page_title="OFFICINE LUPONE - Dashboard",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Usa st.cache_resource per eseguire init_db UNA SOLA VOLTA all'avvio del server
@st.cache_resource
def inizializza_database_una_volta():
    database.init_db()
    return True

try:
    inizializza_database_una_volta()
except Exception as e:
    st.error(f"Errore di connessione al database Neon: {e}")
    
# --- 2. CSS PERSONALIZZATO ---
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

api_key = st.secrets.get("GEMINI_API_KEY", "")

# --- FUNZIONI BACKEND DB ---
def aggiungi_settore_db(nome_settore: str) -> str:
    if not nome_settore or not nome_settore.strip():
        return "❌ Il nome del settore non può essere vuoto!"
    conn = None
    try:
        conn = database.get_connection()
        with conn.cursor() as c:
            c.execute("INSERT INTO settori (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING;", (nome_settore.strip(),))
        conn.commit()
        return f"✅ Settore '{nome_settore}' aggiunto!"
    except Exception as e:
        if conn:
            conn.rollback()
        return f"❌ Errore durante l'inserimento: {e}"
    finally:
        if conn:
            conn.close()

def rinomina_settore_db(vecchio_nome: str, nuovo_nome: str) -> str:
    if not nuovo_nome or not nuovo_nome.strip():
        return "❌ Il nuovo nome non può essere vuoto!"
    conn = None
    try:
        conn = database.get_connection()
        with conn.cursor() as c:
            c.execute("UPDATE settori SET nome = %s WHERE nome = %s", (nuovo_nome.strip(), vecchio_nome))
        conn.commit()
        return f"✅ Settore '{vecchio_nome}' rinominato in '{nuovo_nome}'!"
    except Exception as e:
        if conn:
            conn.rollback()
        return f"❌ Errore: {e}"
    finally:
        if conn:
            conn.close()

def elimina_settore_db(nome_settore: str) -> str:
    conn = None
    try:
        conn = database.get_connection()
        with conn.cursor() as c:
            c.execute("DELETE FROM settori WHERE nome = %s", (nome_settore,))
        conn.commit()
        return f"🗑️ Settore '{nome_settore}' eliminato!"
    except Exception as e:
        if conn:
            conn.rollback()
        return f"❌ Errore: {e}"
    finally:
        if conn:
            conn.close()

def aggiungi_operatore_db(nome_operatore: str, settore_id: int) -> str:
    if not nome_operatore or not nome_operatore.strip():
        return "❌ Il nome dell'operatore non può essere vuoto!"
    conn = None
    try:
        conn = database.get_connection()
        with conn.cursor() as c:
            c.execute("INSERT INTO operatori (nome, settore_id) VALUES (%s, %s)", (nome_operatore.strip(), settore_id))
        conn.commit()
        return f"✅ Operatore '{nome_operatore}' aggiunto!"
    except Exception as e:
        if conn:
            conn.rollback()
        return f"❌ Errore: {e}"
    finally:
        if conn:
            conn.close()

def elimina_operatore_db(operatore_id: int) -> str:
    conn = None
    try:
        conn = database.get_connection()
        with conn.cursor() as c:
            c.execute("DELETE FROM operatori WHERE id = %s", (operatore_id,))
        conn.commit()
        return f"🗑️ Operatore rimosso!"
    except Exception as e:
        if conn:
            conn.rollback()
        return f"❌ Errore: {e}"
    finally:
        if conn:
            conn.close()

def reset_settori_ai(nuovi_settori: list[str]) -> str:
    conn = None
    try:
        conn = database.get_connection()
        with conn.cursor() as c:
            c.execute("TRUNCATE TABLE settori RESTART IDENTITY CASCADE")
            for settore in nuovi_settori:
                if settore.strip():
                    c.execute("INSERT INTO settori (nome) VALUES (%s)", (settore.strip(),))
        conn.commit()
        return f"✅ Settori resettati: {', '.join(nuovi_settori)}"
    except Exception as e:
        if conn:
            conn.rollback()
        return f"❌ Errore: {e}"
    finally:
        if conn:
            conn.close()

def salva_prodotto_esteso(particolare: str, mat_tratt: str, macch_gruppo: str, disegno: str, costo: float, prezzo: float, ore_settori: dict) -> str:
    if not particolare or not particolare.strip():
        return "❌ Il campo 'Particolare' è obbligatorio!"
    conn = None
    try:
        conn = database.get_connection()
        with conn.cursor() as c:
            c.execute("""
                INSERT INTO prodotti (nome, materiale_trattamento, macchina_gruppo_formato, disegno, costo_interno, prezzo_vendita)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT(nome) DO UPDATE SET
                materiale_trattamento=EXCLUDED.materiale_trattamento,
                macchina_gruppo_formato=EXCLUDED.macchina_gruppo_formato,
                disegno=EXCLUDED.disegno,
                costo_interno=EXCLUDED.costo_interno,
                prezzo_vendita=EXCLUDED.prezzo_vendita
                RETURNING id;
            """, (particolare.strip(), mat_tratt.strip(), macch_gruppo.strip(), disegno.strip(), costo, prezzo))
            
            prodotto_id = c.fetchone()[0]
            
            for settore_id, ore in ore_settori.items():
                c.execute("""
                    INSERT INTO prodotto_ore_settori (prodotto_id, settore_id, ore)
                    VALUES (%s, %s, %s)
                    ON CONFLICT(prodotto_id, settore_id) DO UPDATE SET ore=EXCLUDED.ore;
                """, (prodotto_id, settore_id, ore))
                
        conn.commit()
        return f"✅ Prodotto '{particolare}' salvato con successo!"
    except Exception as e:
        if conn:
            conn.rollback()
        return f"❌ Errore durante il salvataggio: {e}"
    finally:
        if conn:
            conn.close()

def elimina_prodotto_db(nome_prodotto: str) -> str:
    conn = None
    try:
        conn = database.get_connection()
        with conn.cursor() as c:
            c.execute("DELETE FROM prodotti WHERE nome = %s", (nome_prodotto,))
        conn.commit()
        return f"🗑️ Prodotto '{nome_prodotto}' eliminato!"
    except Exception as e:
        if conn:
            conn.rollback()
        return f"❌ Errore: {e}"
    finally:
        if conn:
            conn.close()

tools_map = {
    "aggiungi_settore_ai": aggiungi_settore_db,
    "rinomina_settore_ai": rinomina_settore_db,
    "reset_settori_ai": reset_settori_ai
}
tools_list = [aggiungi_settore_db, rinomina_settore_db, reset_settori_ai]

# --- 3. HEADER ---
h_left, h_right = st.columns([3, 1])
with h_left:
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 12px;">
            <div style="background-color: #0e3d2f; color: white; padding: 8px 12px; border-radius: 8px; font-weight: bold;">🛡️</div>
            <div>
                <div class="brand-title">OFFICINE LUPONE - GESTIONALE ENTERPRISE</div>
                <div class="brand-sub">Sistema Integrato AI • Versione 2.5 Cloud</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

st.write("")

# LETTURA DATI DB (Utilizza direttamente l'oggetto connessione psycopg2)
def carica_dati():
    conn = None
    try:
        conn = database.get_connection()
        
        df_settori = pd.read_sql_query('SELECT id AS "ID", nome AS "Nome Settore" FROM settori ORDER BY id', conn)
        
        df_operatori = pd.read_sql_query('''
            SELECT o.id AS "ID", o.nome AS "Nome Operatore", s.nome AS "Settore", o.settore_id 
            FROM operatori o 
            JOIN settori s ON o.settore_id = s.id ORDER BY o.id
        ''', conn)
        
        query_prodotti = '''
            SELECT 
                p.id AS "ID",
                p.nome AS "Particolare",
                p.materiale_trattamento AS "Materiale / Trattamento",
                p.macchina_gruppo_formato AS "Macchina / Gruppo / Formato",
                p.disegno AS "Disegno",
                COALESCE(SUM(pos.ore), 0) AS "Ore Totali",
                p.costo_interno AS "Costo (€)",
                p.prezzo_vendita AS "Prezzo (€)"
            FROM prodotti p
            LEFT JOIN prodotto_ore_settori pos ON p.id = pos.prodotto_id
            GROUP BY p.id, p.nome, p.materiale_trattamento, p.macchina_gruppo_formato, p.disegno, p.costo_interno, p.prezzo_vendita
            ORDER BY p.id;
        '''
        df_prodotti = pd.read_sql_query(query_prodotti, conn)
    except Exception as err:
        st.error(f"Errore lettura dati: {err}")
        df_settori = pd.DataFrame(columns=['ID', 'Nome Settore'])
        df_operatori = pd.DataFrame(columns=['ID', 'Nome Operatore', 'Settore', 'settore_id'])
        df_prodotti = pd.DataFrame(columns=['ID', 'Particolare', 'Materiale / Trattamento', 'Macchina / Gruppo / Formato', 'Disegno', 'Ore Totali', 'Costo (€)', 'Prezzo (€)'])
    finally:
        if conn:
            conn.close()

    return df_settori, df_operatori, df_prodotti

df_settori, df_operatori, df_prodotti = carica_dati()

# --- 4. TABS ---
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
                ⚠️ <b>Nessun settore registrato:</b> Vai nella scheda <b>Settori Produttivi</b> per aggiungerne uno prima di inserire i prodotti.
            </div>
        """, unsafe_allow_html=True)

    c_left, c_right = st.columns(2)
    with c_left:
        st.markdown("### 🏬 Ultimi Settori")
        st.dataframe(df_settori, width="stretch", hide_index=True)
    with c_right:
        st.markdown("### 👷‍♂️ Operatori per Settore")
        if not df_operatori.empty:
            st.dataframe(df_operatori[['Nome Operatore', 'Settore']], width="stretch", hide_index=True)
        else:
            st.info("Nessun operatore assegnato.")

# --- 2. SETTORI PRODUTTIVI ---
with tab_settori:
    st.markdown("## 🏬 Gestione Settori & Operatori")
    st.write("Configura i settori di lavorazione e assegna gli operatori qualificati.")
    
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    
    with col_s1:
        with st.popover("➕ Nuovo Settore", width="stretch"):
            st.write("**Aggiungi Settore**")
            nuovo_s = st.text_input("Nome Settore:", key="set_add_input")
            if st.button("Salva Settore", type="primary", key="btn_add_s"):
                if nuovo_s:
                    msg = aggiungi_settore_db(nuovo_s)
                    st.toast(msg)
                    st.rerun()

    with col_s2:
        with st.popover("✏️ Rinomina Settore", width="stretch"):
            if not df_settori.empty:
                s_sel = st.selectbox("Seleziona da rinominare:", df_settori['Nome Settore'].tolist(), key="set_ren_sel")
                s_new = st.text_input("Nuovo nome:", value=s_sel, key="set_ren_txt")
                if st.button("Conferma Rinomina", type="primary", key="btn_ren_s"):
                    msg = rinomina_settore_db(s_sel, s_new)
                    st.toast(msg)
                    st.rerun()
            else:
                st.info("Nessun settore presente.")

    with col_s3:
        with st.popover("🗑 Elimina Settore", width="stretch"):
            if not df_settori.empty:
                s_del = st.selectbox("Seleziona da eliminare:", df_settori['Nome Settore'].tolist(), key="set_del_sel")
                if st.button("Conferma Eliminazione", type="secondary", key="btn_del_s"):
                    msg = elimina_settore_db(s_del)
                    st.toast(msg)
                    st.rerun()
            else:
                st.info("Nessun settore presente.")

    with col_s4:
        with st.popover("👷‍♂ Aggiungi Operatore", width="stretch"):
            st.write("**Nuovo Operatore**")
            if not df_settori.empty:
                set_target = st.selectbox("Assegna al Settore:", df_settori['Nome Settore'].tolist(), key="op_set_target")
                op_nome = st.text_input("Nome e Cognome Operatore:", key="op_name_input")
                if st.button("Salva Operatore", type="primary", key="btn_add_op"):
                    if op_nome:
                        s_id = df_settori[df_settori['Nome Settore'] == set_target]['ID'].values[0]
                        msg = aggiungi_operatore_db(op_nome, int(s_id))
                        st.toast(msg)
                        st.rerun()
            else:
                st.info("Crea prima almeno un settore.")

    st.write("")
    
    if not df_settori.empty:
        col_m1, col_m2 = st.columns(2)
        for i, row in df_settori.iterrows():
            target_col = col_m1 if i % 2 == 0 else col_m2
            with target_col:
                with st.container(border=True):
                    st.markdown(f"### 🏭 {row['Nome Settore']}")
                    
                    ops = df_operatori[df_operatori['settore_id'] == row['ID']] if not df_operatori.empty else pd.DataFrame()
                    
                    if not ops.empty:
                        st.write("**Operatori Assegnati:**")
                        for _, op_row in ops.iterrows():
                            c_op1, c_op2 = st.columns([4, 1])
                            with c_op1:
                                st.write(f"• 👤 **{op_row['Nome Operatore']}**")
                            with c_op2:
                                if st.button("🗑️", key=f"del_op_{op_row['ID']}", help="Rimuovi operatore"):
                                    msg = elimina_operatore_db(op_row['ID'])
                                    st.toast(msg)
                                    st.rerun()
                    else:
                        st.caption("Nessun operatore inserito per questo settore.")
    else:
        st.info("Nessun settore disponibile.")

# --- 3. CATALOGO PRODOTTI ---
with tab_prodotti:
    st.markdown("## 📋 Catalogo Prodotti e Listino")
    st.write("Gestisci il catalogo prodotti con specifica dei campi dettagliati e delle ore per settore.")

    cp1, cp2 = st.columns(2)
    with cp1:
        with st.popover("➕ Aggiungi Prodotto Completo", width="stretch"):
            st.markdown("### 📝 Dettagli Prodotto / Particolare")
            
            p_particolare = st.text_input("Particolare (Nome Prodotto):", key="inp_part")
            p_mat_tratt = st.text_input("Materiale / Trattamento:", key="inp_mat")
            p_macch_grup = st.text_input("Macchina / Gruppo / Formato:", key="inp_macch")
            p_disegno = st.text_input("Disegno (Codice o Riferimento):", key="inp_dis")
            
            st.markdown("---")
            st.markdown("⏱️ **Ore di lavoro per ogni Settore di Produzione**")
            
            ore_settori_dict = {}
            if not df_settori.empty:
                for _, s_row in df_settori.iterrows():
                    val_ore = st.number_input(
                        f"Ore per settore: {s_row['Nome Settore']}", 
                        min_value=0.0, 
                        step=0.5, 
                        key=f"ore_set_{s_row['ID']}"
                    )
                    ore_settori_dict[int(s_row['ID'])] = val_ore
            else:
                st.warning("Nessun settore di produzione presente. Aggiungili nella scheda 'Settori Produttivi'.")
                
            st.markdown("---")
            st.markdown("💰 **Costi e Prezzi**")
            p_costo = st.number_input("Costo Interno (€):", min_value=0.0, step=10.0, key="inp_costo")
            p_prezzo = st.number_input("Prezzo di Vendita (€):", min_value=0.0, step=10.0, key="inp_prezzo")
            
            if st.button("Salva Prodotto Nel Database", type="primary", key="btn_salva_prod_full"):
                if p_particolare:
                    esito = salva_prodotto_esteso(
                        p_particolare, 
                        p_mat_tratt, 
                        p_macch_grup, 
                        p_disegno, 
                        p_costo, 
                        p_prezzo, 
                        ore_settori_dict
                    )
                    st.toast(esito)
                    st.rerun()
                else:
                    st.error("Il campo 'Particolare' è obbligatorio!")

    with cp2:
        with st.popover("🗑 Elimina Prodotto", width="stretch"):
            if not df_prodotti.empty:
                pr_del = st.selectbox("Seleziona Prodotto:", df_prodotti['Particolare'].tolist(), key="p_del_sel")
                if st.button("Conferma Eliminazione", type="secondary", key="btn_del_p"):
                    msg = elimina_prodotto_db(pr_del)
                    st.toast(msg)
                    st.rerun()
            else:
                st.info("Nessun prodotto a catalogo.")

    st.write("")
    
    st.dataframe(
        df_prodotti, 
        width="stretch", 
        hide_index=True,
        column_config={
            "Costo (€)": st.column_config.NumberColumn(format="€ %.2f"),
            "Prezzo (€)": st.column_config.NumberColumn(format="€ %.2f"),
            "Ore Totali": st.column_config.NumberColumn(format="%.1f h")
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
            modelli_validi = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
            
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
