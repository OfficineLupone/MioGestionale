import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import database

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="OFFICINE LUPONE - Enterprise",
    page_icon="⚙",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inizializzazione sicura DB
@st.cache_resource
def inizializza_db_sicuro():
    try:
        database.init_db()
        return True
    except Exception as e:
        return str(e)

db_status = inizializza_db_sicuro()
if db_status is not True:
    st.error(f"⚠️ Impossibile connettersi al database Neon: {db_status}")

# --- 2. CSS PERSONALIZZATO (DESIGN ENTERPRISE PREMIUM) ---
st.markdown("""
    <style>
    /* Google Fonts Import */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background-color: #f8fafc;
    }
    
    #MainMenu, footer, header { visibility: hidden; }

    /* Custom Header Container */
    .header-container {
        background: linear-gradient(135deg, #0b3c2d 0%, #14523e 100%);
        padding: 22px 28px;
        border-radius: 14px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(11, 60, 45, 0.25);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .brand-title {
        font-weight: 800;
        font-size: 1.4rem;
        letter-spacing: -0.5px;
        color: #ffffff;
        margin: 0;
    }

    .brand-sub {
        font-size: 0.85rem;
        color: #a7f3d0;
        margin-top: 2px;
    }

    .status-badge {
        background-color: rgba(255, 255, 255, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.25);
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        color: #e6fffa;
        backdrop-filter: blur(4px);
    }

    /* Cards metriche */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        transition: all 0.2s ease-in-out;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.06);
        border-color: #cbd5e1;
    }

    /* Product Card */
    .product-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 16px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
        transition: all 0.2s ease;
    }

    .product-card:hover {
        border-color: #10b981;
        box-shadow: 0 6px 15px rgba(0,0,0,0.05);
    }

    .product-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 6px;
    }

    .badge-tag {
        display: inline-block;
        background-color: #f1f5f9;
        color: #475569;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 6px;
        margin-right: 6px;
    }

    /* Standard Button Styling Override */
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #0b3c2d 0%, #14523e 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 4px rgba(11, 60, 45, 0.2) !important;
    }

    .stButton>button[kind="primary"]:hover {
        opacity: 0.92 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 8px rgba(11, 60, 45, 0.3) !important;
    }

    .stButton>button[kind="secondary"] {
        border-radius: 8px !important;
        border: 1px solid #cbd5e1 !important;
        font-weight: 500 !important;
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #e2e8f0;
        padding: 6px;
        border-radius: 10px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 42px;
        border-radius: 7px;
        font-weight: 600;
        font-size: 0.9rem;
        color: #475569;
        background-color: transparent;
        border: none !important;
    }

    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #0b3c2d !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    </style>
""", unsafe_allow_html=True)

api_key = st.secrets.get("GEMINI_API_KEY", "")

# --- 3. FUNZIONI OPERATIVE DB ---
def aggiungi_settore_db(nome_settore: str) -> str:
    if not nome_settore or not str(nome_settore).strip():
        return "❌ Il nome del settore non può essere vuoto!"
    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute("INSERT INTO settori (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING;", (str(nome_settore).strip(),))
            conn.commit()
        st.cache_data.clear()
        return f"✅ Settore '{nome_settore}' aggiunto!"
    except Exception as e:
        return f"❌ Errore: {e}"

def rinomina_settore_db(vecchio_nome: str, nuovo_nome: str) -> str:
    if not nuovo_nome or not str(nuovo_nome).strip():
        return "❌ Il nuovo nome non può essere vuoto!"
    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute("UPDATE settori SET nome = %s WHERE nome = %s", (str(nuovo_nome).strip(), str(vecchio_nome).strip()))
            conn.commit()
        st.cache_data.clear()
        return f"✅ Settore '{vecchio_nome}' rinominato in '{nuovo_nome}'!"
    except Exception as e:
        return f"❌ Errore: {e}"

def elimina_settore_db(nome_settore: str) -> str:
    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute("DELETE FROM settori WHERE nome = %s", (str(nome_settore).strip(),))
            conn.commit()
        st.cache_data.clear()
        return f"🗑️️ Settore '{nome_settore}' eliminato!"
    except Exception as e:
        return f"❌ Errore: {e}"

def aggiungi_operatore_db(nome_operatore: str, settore_id: int) -> str:
    if not nome_operatore or not str(nome_operatore).strip():
        return "❌ Il nome dell'operatore non può essere vuoto!"
    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute("INSERT INTO operatori (nome, settore_id) VALUES (%s, %s)", (str(nome_operatore).strip(), int(settore_id)))
            conn.commit()
        st.cache_data.clear()
        return f"✅ Operatore '{nome_operatore}' aggiunto!"
    except Exception as e:
        return f"❌ Errore: {e}"

def elimina_operatore_db(operatore_id: int) -> str:
    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute("DELETE FROM operatori WHERE id = %s", (int(operatore_id),))
            conn.commit()
        st.cache_data.clear()
        return f"🗑️ Operatore rimosso!"
    except Exception as e:
        return f"❌ Errore: {e}"

def reset_settori_ai(nuovi_settori: list[str]) -> str:
    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute("TRUNCATE TABLE settori RESTART IDENTITY CASCADE")
                for settore in nuovi_settori:
                    if settore and str(settore).strip():
                        c.execute("INSERT INTO settori (nome) VALUES (%s)", (str(settore).strip(),))
            conn.commit()
        st.cache_data.clear()
        return f"✅ Settori resettati: {', '.join(nuovi_settori)}"
    except Exception as e:
        return f"❌ Errore: {e}"

def salva_prodotto_esteso(
    particolare: str,
    mat_tratt: str = "",
    macch_gruppo: str = "",
    disegno: str = "",
    costo: float = 0.0,
    prezzo: float = 0.0,
    ore_settori: dict = None,
    prodotto_id: int = None
) -> str:
    if not particolare or not str(particolare).strip():
        return "❌ Il campo 'Particolare' è obbligatorio!"

    particolare = str(particolare).strip()
    mat_tratt = str(mat_tratt or "").strip()
    macch_gruppo = str(macch_gruppo or "").strip()
    disegno = str(disegno or "").strip()
    
    try:
        costo_val = float(costo or 0.0)
        prezzo_val = float(prezzo or 0.0)
    except (ValueError, TypeError):
        return "❌ Costo e Prezzo devono essere numeri validi!"

    ore_totali = 0.0
    if isinstance(ore_settori, dict):
        for val in ore_settori.values():
            try:
                ore_totali += float(val or 0.0)
            except (ValueError, TypeError):
                pass

    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                if prodotto_id:
                    c.execute("""
                        UPDATE prodotti SET
                            nome = %s,
                            ore_lavorazione = %s,
                            costo_interno = %s,
                            prezzo_vendita = %s,
                            materiale_trattamento = %s,
                            macchina_gruppo_formato = %s,
                            disegno = %s
                        WHERE id = %s
                        RETURNING id;
                    """, (particolare, ore_totali, costo_val, prezzo_val, mat_tratt, macch_gruppo, disegno, int(prodotto_id)))
                    p_id = prodotto_id
                else:
                    c.execute("""
                        INSERT INTO prodotti (
                            nome, ore_lavorazione, costo_interno, prezzo_vendita, 
                            materiale_trattamento, macchina_gruppo_formato, disegno
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT(nome) DO UPDATE SET
                            ore_lavorazione = EXCLUDED.ore_lavorazione,
                            costo_interno = EXCLUDED.costo_interno,
                            prezzo_vendita = EXCLUDED.prezzo_vendita,
                            materiale_trattamento = EXCLUDED.materiale_trattamento,
                            macchina_gruppo_formato = EXCLUDED.macchina_gruppo_formato,
                            disegno = EXCLUDED.disegno
                        RETURNING id;
                    """, (particolare, ore_totali, costo_val, prezzo_val, mat_tratt, macch_gruppo, disegno))
                    res = c.fetchone()
                    if not res:
                        return "❌ Errore durante il salvataggio."
                    p_id = res[0]
                
                if isinstance(ore_settori, dict):
                    for settore_id, ore in ore_settori.items():
                        try:
                            s_id = int(settore_id)
                            val_ore = float(ore or 0.0)
                        except (ValueError, TypeError):
                            continue

                        if val_ore > 0:
                            c.execute("""
                                INSERT INTO prodotto_ore_settori (prodotto_id, settore_id, ore)
                                VALUES (%s, %s, %s)
                                ON CONFLICT(prodotto_id, settore_id) DO UPDATE SET ore = EXCLUDED.ore;
                            """, (p_id, s_id, val_ore))
                        else:
                            c.execute("""
                                DELETE FROM prodotto_ore_settori 
                                WHERE prodotto_id = %s AND settore_id = %s;
                            """, (p_id, s_id))

            conn.commit()
        st.cache_data.clear()
        return f"✅ Prodotto '{particolare}' salvato!"
    except Exception as e:
        return f"❌ Errore: {e}"

def elimina_prodotto_db(nome_prodotto: str) -> str:
    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute("DELETE FROM prodotti WHERE nome = %s", (str(nome_prodotto).strip(),))
            conn.commit()
        st.cache_data.clear()
        return f"🗑️ Prodotto '{nome_prodotto}' eliminato!"
    except Exception as e:
        return f"❌ Errore: {e}"

def ottieni_ore_prodotto_settori(prodotto_id: int) -> dict:
    """Recupera la ripartizione delle ore per settore di un determinato prodotto."""
    dati = {}
    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute("SELECT settore_id, ore FROM prodotto_ore_settori WHERE prodotto_id = %s", (int(prodotto_id),))
                rows = c.fetchall()
                for r in rows:
                    dati[r[0]] = float(r[1])
    except Exception:
        pass
    return dati

# Mappatura tool per l'IA
tools_map = {
    "aggiungi_settore_db": aggiungi_settore_db,
    "rinomina_settore_db": rinomina_settore_db,
    "elimina_settore_db": elimina_settore_db,
    "aggiungi_operatore_db": aggiungi_operatore_db,
    "elimina_operatore_db": elimina_operatore_db,
    "reset_settori_ai": reset_settori_ai,
    "salva_prodotto_esteso": salva_prodotto_esteso,
    "elimina_prodotto_db": elimina_prodotto_db
}
tools_list = list(tools_map.values())

# --- 4. CARICAMENTO DATI ---
@st.cache_data(ttl=5)
def carica_dati():
    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                # Settori
                c.execute('SELECT id AS "ID", nome AS "Nome Settore" FROM settori ORDER BY id')
                rows_settori = c.fetchall()
                cols_settori = [desc[0] for desc in c.description] if c.description else ["ID", "Nome Settore"]
                df_settori = pd.DataFrame(rows_settori, columns=cols_settori)

                # Operatori
                c.execute('''
                    SELECT o.id AS "ID", o.nome AS "Nome Operatore", s.nome AS "Settore", o.settore_id 
                    FROM operatori o 
                    JOIN settori s ON o.settore_id = s.id ORDER BY o.id
                ''')
                rows_op = c.fetchall()
                cols_op = [desc[0] for desc in c.description] if c.description else ["ID", "Nome Operatore", "Settore", "settore_id"]
                df_operatori = pd.DataFrame(rows_op, columns=cols_op)

                # Prodotti
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
                c.execute(query_prodotti)
                rows_prod = c.fetchall()
                cols_prod = [desc[0] for desc in c.description] if c.description else ["ID", "Particolare", "Materiale / Trattamento", "Macchina / Gruppo / Formato", "Disegno", "Ore Totali", "Costo (€)", "Prezzo (€)"]
                df_prodotti = pd.DataFrame(rows_prod, columns=cols_prod)

        return df_settori, df_operatori, df_prodotti
    except Exception as e:
        st.error(f"Errore lettura DB: {e}")
        return (
            pd.DataFrame(columns=['ID', 'Nome Settore']),
            pd.DataFrame(columns=['ID', 'Nome Operatore', 'Settore', 'settore_id']),
            pd.DataFrame(columns=['ID', 'Particolare', 'Materiale / Trattamento', 'Macchina / Gruppo / Formato', 'Disegno', 'Ore Totali', 'Costo (€)', 'Prezzo (€)'])
        )

df_settori, df_operatori, df_prodotti = carica_dati()

# --- 5. HEADER DESIGN ---
st.markdown("""
    <div class="header-container">
        <div>
            <div class="brand-title">⚙ OFFICINE LUPONE</div>
            <div class="brand-sub">Sistema Gestionale Integrato & AI Copilot</div>
        </div>
        <div class="status-badge">
            🟢 Online • DB Neon Cloud
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 6. TABS INTERFACCIA ---
tab_panoramica, tab_settori, tab_prodotti, tab_assistente = st.tabs([
    "📊 Panoramica", 
    "🏬 Settori & Operatori", 
    "📋 Catalogo Prodotti", 
    "💬 Assistente IA"
])

# --- TAB PANORAMICA ---
with tab_panoramica:
    st.markdown("### 📈 Stato Aziendale")
    k1, k2, k3 = st.columns(3)
    k1.metric("Settori Attivi", len(df_settori))
    k2.metric("Operatori Registrati", len(df_operatori))
    k3.metric("Prodotti in Catalogo", len(df_prodotti))
    
    st.write("")
    c_left, c_right = st.columns(2)
    with c_left:
        st.markdown("#### 🏬 Struttura Settori")
        st.dataframe(df_settori, use_container_width=True, hide_index=True)
    with c_right:
        st.markdown("#### 👷‍♂️ Mappa Operatori")
        st.dataframe(df_operatori[['Nome Operatore', 'Settore']] if not df_operatori.empty else df_operatori, use_container_width=True, hide_index=True)

# --- TAB SETTORI ---
with tab_settori:
    st.markdown("### 🏬 Gestione Settori & Operatori")
    
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        with st.popover("➕ Nuovo Settore", use_container_width=True):
            nuovo_s = st.text_input("Nome Settore:")
            if st.button("Salva Settore", type="primary", key="btn_add_s"):
                if nuovo_s:
                    st.toast(aggiungi_settore_db(nuovo_s))
                    st.rerun()

    with col_s2:
        with st.popover("✏️ Rinomina Settore", use_container_width=True):
            if not df_settori.empty:
                s_sel = st.selectbox("Seleziona:", df_settori['Nome Settore'].tolist(), key="sb_ren_s")
                s_new = st.text_input("Nuovo nome:", value=s_sel, key="ti_ren_s")
                if st.button("Conferma Rinomina", type="primary", key="btn_ren_s"):
                    st.toast(rinomina_settore_db(s_sel, s_new))
                    st.rerun()

    with col_s3:
        with st.popover("🗑 Elimina Settore", use_container_width=True):
            if not df_settori.empty:
                s_del = st.selectbox("Seleziona da eliminare:", df_settori['Nome Settore'].tolist(), key="sb_del_s")
                if st.button("Conferma Eliminazione", key="btn_del_s"):
                    st.toast(elimina_settore_db(s_del))
                    st.rerun()

    with col_s4:
        with st.popover("👷‍♂️ Aggiungi Operatore", use_container_width=True):
            if not df_settori.empty:
                set_target = st.selectbox("Assegna al Settore:", df_settori['Nome Settore'].tolist(), key="sb_op_s")
                op_nome = st.text_input("Nome Operatore:", key="ti_op_n")
                if st.button("Salva Operatore", type="primary", key="btn_add_op"):
                    if op_nome:
                        s_id = df_settori[df_settori['Nome Settore'] == set_target]['ID'].values[0]
                        st.toast(aggiungi_operatore_db(op_nome, int(s_id)))
                        st.rerun()

    st.write("")
    st.dataframe(df_settori, use_container_width=True, hide_index=True)

# --- TAB CATALOGO PRODOTTI (CON MODIFICA ED ELIMINAZIONE) ---
with tab_prodotti:
    st.markdown("### 📋 Catalogo Prodotti")
    
    # Bottone principale Aggiungi
    top_col1, top_col2 = st.columns([1, 4])
    with top_col1:
        with st.popover("➕ Aggiungi Nuovo Prodotto", use_container_width=True):
            st.subheader("Crea Nuovo Prodotto")
            p_particolare = st.text_input("Particolare (Nome):", key="new_p_name")
            p_mat_tratt = st.text_input("Materiale / Trattamento:", key="new_p_mat")
            p_macch_grup = st.text_input("Macchina / Gruppo:", key="new_p_macch")
            p_disegno = st.text_input("Disegno:", key="new_p_dis")
            
            st.markdown("**Ripartizione Ore Settori:**")
            ore_settori_dict = {}
            if not df_settori.empty:
                for _, s_row in df_settori.iterrows():
                    val_ore = st.number_input(f"Ore {s_row['Nome Settore']}:", min_value=0.0, step=0.5, key=f"new_ore_{s_row['ID']}")
                    if val_ore > 0:
                        ore_settori_dict[int(s_row['ID'])] = val_ore
                    
            p_costo = st.number_input("Costo Interno (€):", min_value=0.0, step=10.0, key="new_p_costo")
            p_prezzo = st.number_input("Prezzo Vendita (€):", min_value=0.0, step=10.0, key="new_p_prezzo")
            
            if st.button("💾 Salva Prodotto", type="primary", key="btn_save_new_p"):
                if p_particolare and p_particolare.strip():
                    esito = salva_prodotto_esteso(
                        particolare=p_particolare,
                        mat_tratt=p_mat_tratt,
                        macch_gruppo=p_macch_grup,
                        disegno=p_disegno,
                        costo=p_costo,
                        prezzo=p_prezzo,
                        ore_settori=ore_settori_dict
                    )
                    st.toast(esito)
                    if "✅" in esito:
                        st.rerun()
                else:
                    st.warning("⚠️ Il campo 'Particolare' è obbligatorio!")

    st.write("")

    # Visualizzazione Card Prodotti con Azioni In-Line Modifica ed Elimina
    if df_prodotti.empty:
        st.info("Nessun prodotto disponibile in catalogo. Aggiungine uno per iniziare!")
    else:
        for idx, row in df_prodotti.iterrows():
            p_id = row['ID']
            p_nome = row['Particolare']
            p_mat = row['Materiale / Trattamento'] or "-"
            p_macch = row['Macchina / Gruppo / Formato'] or "-"
            p_dis = row['Disegno'] or "-"
            p_ore = row['Ore Totali']
            p_costo_v = row['Costo (€)']
            p_prezzo_v = row['Prezzo (€)']

            with st.container():
                col_info, col_actions = st.columns([4, 1])
                
                with col_info:
                    st.markdown(f"""
                        <div class="product-card">
                            <div class="product-title">📦 {p_nome}</div>
                            <div>
                                <span class="badge-tag">Mat: {p_mat}</span>
                                <span class="badge-tag">Macchina: {p_macch}</span>
                                <span class="badge-tag">Disegno: {p_dis}</span>
                            </div>
                            <div style="margin-top: 10px; font-size: 0.9rem; color: #334155;">
                                ⏱️ <b>Ore Totali:</b> {p_ore:.1f}h &nbsp;|&nbsp; 
                                💵 <b>Costo:</b> €{p_costo_v:.2f} &nbsp;|&nbsp; 
                                🏷️ <b>Prezzo:</b> €{p_prezzo_v:.2f}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                with col_actions:
                    # Popover Modifica
                    with st.popover("✏️ Modifica", use_container_width=True):
                        st.markdown(f"**Modifica Prodotto:** {p_nome}")
                        edit_nome = st.text_input("Particolare:", value=p_nome, key=f"edit_nome_{p_id}")
                        edit_mat = st.text_input("Materiale / Trattamento:", value=p_mat if p_mat != "-" else "", key=f"edit_mat_{p_id}")
                        edit_macch = st.text_input("Macchina / Gruppo:", value=p_macch if p_macch != "-" else "", key=f"edit_macch_{p_id}")
                        edit_dis = st.text_input("Disegno:", value=p_dis if p_dis != "-" else "", key=f"edit_dis_{p_id}")
                        
                        # Recupera e imposta le ore correnti del prodotto
                        ore_esistenti = ottieni_ore_prodotto_settori(p_id)
                        edit_ore_dict = {}
                        
                        if not df_settori.empty:
                            st.markdown("**Ripartizione Ore:**")
                            for _, s_row in df_settori.iterrows():
                                s_id_curr = int(s_row['ID'])
                                ore_val_curr = ore_esistenti.get(s_id_curr, 0.0)
                                v_ore = st.number_input(
                                    f"Ore {s_row['Nome Settore']}:", 
                                    min_value=0.0, 
                                    value=float(ore_val_curr), 
                                    step=0.5, 
                                    key=f"edit_ore_{p_id}_{s_id_curr}"
                                )
                                if v_ore > 0:
                                    edit_ore_dict[s_id_curr] = v_ore

                        edit_costo = st.number_input("Costo (€):", min_value=0.0, value=float(p_costo_v), step=10.0, key=f"edit_costo_{p_id}")
                        edit_prezzo = st.number_input("Prezzo (€):", min_value=0.0, value=float(p_prezzo_v), step=10.0, key=f"edit_prezzo_{p_id}")

                        if st.button("Aggiorna Prodotto", type="primary", key=f"btn_update_{p_id}"):
                            esito = salva_prodotto_esteso(
                                particolare=edit_nome,
                                mat_tratt=edit_mat,
                                macch_gruppo=edit_macch,
                                disegno=edit_dis,
                                costo=edit_costo,
                                prezzo=edit_prezzo,
                                ore_settori=edit_ore_dict,
                                prodotto_id=p_id
                            )
                            st.toast(esito)
                            st.rerun()

                    # Bottone Elimina
                    if st.button("🗑️ Elimina", key=f"btn_del_prod_{p_id}", use_container_width=True):
                        st.toast(elimina_prodotto_db(p_nome))
                        st.rerun()

# --- TAB ASSISTENTE IA ---
with tab_assistente:
    st.markdown("### 💬 Assistente Virtuale Copilot")
    st.caption("Fornisci istruzioni in linguaggio naturale per gestire il database in tempo reale.")
    
    cmd = st.text_input("Impartisci un comando all'IA:", placeholder="Es. Aggiungi il settore Tranciatura, oppure elimina il prodotto X...")
    
    if st.button("🚀 Esegui Comando", type="primary", key="btn_exec_ai") and cmd:
        if api_key:
            client = genai.Client(api_key=api_key)
            
            with st.spinner("Elaborazione del comando..."):
                try:
                    system_context = f"""
                    Sei l'assistente per il gestionale di Officine Lupone.
                    Contesto Attuale del Database:
                    - Settori Esistenti: {df_settori.to_dict(orient='records')}
                    - Operatori Esistenti: {df_operatori[['ID', 'Nome Operatore', 'Settore']].to_dict(orient='records')}
                    - Prodotti Esistenti: {df_prodotti[['ID', 'Particolare']].to_dict(orient='records')}
                    
                    Se l'utente chiede un'azione, usa la funzione appropriata dai tool forniti.
                    """

                    response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[system_context, cmd],
                        config=types.GenerateContentConfig(
                            tools=tools_list, 
                            temperature=0
                        )
                    )
                    
                    executed_any = False
                    if getattr(response, 'function_calls', None):
                        for fn_call in response.function_calls:
                            if fn_call.name in tools_map:
                                args = dict(fn_call.args) if fn_call.args else {}
                                res = tools_map[fn_call.name](**args)
                                st.success(res)
                                executed_any = True
                    
                    if executed_any:
                        st.cache_data.clear()
                        st.rerun()
                    elif getattr(response, 'text', None):
                        st.info(response.text)
                    else:
                        st.warning("Il modello non ha identificato comandi eseguibili.")
                        
                except Exception as e:
                    st.error(f"Si è verificato un errore durante l'elaborazione: {e}")
        else:
            st.error("Configura la chiave GEMINI_API_KEY nei secrets!")
