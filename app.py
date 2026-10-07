import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime, date
from google import genai
from sqlalchemy import text
from database import init_db, get_db_engine

# Configurazione Pagina
st.set_page_config(
    page_title="Lupone Enterprise",
    page_icon="🟢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inizializzazione Database
@st.cache_resource
def run_db_init():
    try:
        init_db()
        engine = get_db_engine()
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE public.aziende ADD COLUMN IF NOT EXISTS citta TEXT;"))
            conn.execute(text("ALTER TABLE public.aziende ADD COLUMN IF NOT EXISTS provincia TEXT;"))
            conn.execute(text("ALTER TABLE public.aziende ADD COLUMN IF NOT EXISTS cap TEXT;"))
            conn.execute(text("ALTER TABLE public.prodotti ADD COLUMN IF NOT EXISTS note TEXT;"))
    except Exception as e:
        st.error(f"Errore nell'inizializzazione del database: {e}")

run_db_init()

# Funzioni di fetch caching
@st.cache_data(ttl=60)
def load_settori():
    engine = get_db_engine()
    return pd.read_sql("SELECT * FROM public.settori ORDER BY nome", engine)

@st.cache_data(ttl=60)
def load_operatori():
    engine = get_db_engine()
    return pd.read_sql("""
        SELECT o.id, o.nome as operatore, s.nome as settore, o.settore_id
        FROM public.operatori o LEFT JOIN public.settori s ON o.settore_id = s.id
        ORDER BY o.nome
    """, engine)

@st.cache_data(ttl=60)
def load_aziende():
    engine = get_db_engine()
    return pd.read_sql("SELECT * FROM public.aziende ORDER BY ragione_sociale", engine)

@st.cache_data(ttl=60)
def load_prodotti():
    engine = get_db_engine()
    return pd.read_sql("SELECT * FROM public.prodotti ORDER BY nome", engine)

# =========================================================
# STILE GRAFICO PERSONALIZZATO E MODERNO
# =========================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
        background-color: #F8F9FA !important;
        color: #111827 !important;
    }

    /* Header */
    .brand-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 0px 20px 0px;
        border-bottom: 1px solid #E5E7EB;
        margin-bottom: 20px;
    }
    .brand-icon {
        background-color: #0B3C2D;
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 20px;
    }
    
    /* Design Tabelle Streamlit (rimozione bordi pesanti, intestazioni morbide) */
    [data-testid="stDataFrame"] > div {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #E5E7EB !important;
    }
    [data-testid="stDataFrame"] th {
        background-color: #F3F4F6 !important;
        color: #374151 !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        text-transform: uppercase;
    }
    [data-testid="stDataFrame"] td {
        font-size: 14px !important;
        color: #1F2937 !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent !important;
        gap: 24px !important;
        border-bottom: 1px solid #E5E7EB !important;
    }
    .stTabs [data-baseweb="tab"] {
        height: 46px !important;
        background-color: transparent !important;
        border: none !important;
        border-bottom: 3px solid transparent !important;
        color: #4B5563 !important;
        font-weight: 500 !important;
    }
    .stTabs [aria-selected="true"] {
        color: #0B3C2D !important;
        font-weight: 700 !important;
        border-bottom-color: #0B3C2D !important;
    }

    /* Pulsanti */
    .stButton > button, div[data-testid="stFormSubmitButton"] > button {
        border-radius: 6px !important;
        font-weight: 600 !important;
        padding: 6px 12px !important;
        transition: all 0.2s;
    }
    .btn-action-outline {
        border: 1px solid #D1D5DB !important;
        color: #374151 !important;
        background-color: white !important;
    }
    .btn-action-outline:hover {
        background-color: #F3F4F6 !important;
    }

    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
    }
</style>
""", unsafe_allow_html=True)

# Generator PDF Professionale
def genera_pdf_preventivo(id_preventivo, ragione_sociale, citta, provincia, cap, piva, data, articoli, totale):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 14)
    pdf.set_text_color(11, 60, 45)
    pdf.cell(100, 6, "GESTIONALE LUPONE S.R.L.", ln=False)
    pdf.set_font("Helvetica", 'B', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(90, 5, "Spett.le Cliente:", ln=True, align='R')
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(100, 5, "Via dell'Industria, 45 - 20100 Milano (MI)", ln=False)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.set_text_color(17, 24, 39)
    pdf.cell(90, 5, str(ragione_sociale), ln=True, align='R')
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(100, 5, "P.IVA: 01234567890 | info@enterprise.it", ln=False)
    loc_str = f"{citta or ''} ({provincia or ''}) {cap or ''}".strip()
    pdf.cell(90, 5, loc_str if loc_str else "-", ln=True, align='R')
    pdf.cell(100, 5, "Tel: +39 02 1234567", ln=False)
    piva_str = f"P.IVA / C.F.: {piva}" if piva else ""
    pdf.cell(90, 5, piva_str, ln=True, align='R')
    pdf.ln(10)
    pdf.set_draw_color(229, 231, 235)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.set_text_color(11, 60, 45)
    pdf.cell(0, 8, f"OFFERTA PREVENTIVO N. {id_preventivo} DEL {data}", ln=True)
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(70, 70, 70)
    pdf.multi_cell(0, 5, "Con la presente Vi inviamo la nostra migliore offerta commerciale per i prodotti/servizi sotto specificati:")
    pdf.ln(4)
    pdf.set_fill_color(11, 60, 45)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", 'B', 9)
    pdf.cell(95, 8, " Prodotto / Descrizione", border=1, fill=True)
    pdf.cell(20, 8, "Q.ta", border=1, align='C', fill=True)
    pdf.cell(35, 8, "Prezzo Unit. (EUR)", border=1, align='R', fill=True)
    pdf.cell(40, 8, "Totale (EUR)", border=1, align='R', fill=True)
    pdf.ln()
    pdf.set_text_color(30, 30, 30)
    pdf.set_font("Helvetica", size=9)
    fill_bg = False
    for art in articoli:
        pdf.set_fill_color(248, 249, 250) if fill_bg else pdf.set_fill_color(255, 255, 255)
        p_name = str(art['prodotto'])[:48]
        pdf.cell(95, 8, f" {p_name}", border=1, fill=True)
        pdf.cell(20, 8, str(art['quantita']), border=1, align='C', fill=True)
        # Protezione per prezzo unitario in caso manchi
        pu = art.get('prezzo_unitario') or 0.0
        pdf.cell(35, 8, f"{pu:,.2f}", border=1, align='R', fill=True)
        pdf.cell(40, 8, f"{art['prezzo_totale']:,.2f}", border=1, align='R', fill=True)
        pdf.ln()
        fill_bg = not fill_bg
    pdf.ln(4)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.set_text_color(11, 60, 45)
    pdf.cell(150, 8, "TOTALE GENERALE (IVA Esclusa): ", align='R')
    pdf.cell(40, 8, f"{totale:,.2f} EUR", align='R')
    pdf.ln(10)
    pdf.set_font("Helvetica", 'I', 8)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 4, "Condizioni di pagamento: Rimessa Diretta / Bonifico Bancario", ln=True)
    pdf.cell(0, 4, "Validita offerta: 30 giorni dalla data di emissione", ln=True)
    
    output_str = pdf.output(dest='S')
    return output_str.encode('latin1') if isinstance(output_str, str) else bytes(output_str)

@st.cache_resource
def get_gemini_client():
    api_key = st.secrets.get("GEMINI_API_KEY")
    return genai.Client(api_key=api_key) if api_key else None

client = get_gemini_client()

# Header
st.markdown("""
<div class="brand-header">
    <div style="display: flex; align-items: center; gap: 12px;">
        <div class="brand-icon">🟢</div>
        <div>
            <div style="font-weight: 700; font-size: 18px; color: #111827;">GESTIONALE ENTERPRISE</div>
            <div style="font-size: 12px; color: #6B7280;">Piattaforma di Gestione Aziendale e Ordini</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

tab_dash, tab_aziende, tab_settori_op, tab_prodotti, tab_prev, tab_lav, tab_rep, tab_ai = st.tabs([
    "Panoramica", "Aziende", "Settori & Operatori",
    "Prodotti", "Preventivi", "Lavorazione",
    "Report", "Assistente AI"
])

engine = get_db_engine()

# ---------------------------------------------------------
# 1. PANORAMICA
# ---------------------------------------------------------
with tab_dash:
    st.subheader("Panoramica")
    prodotti_count = pd.read_sql("SELECT COUNT(*) FROM public.prodotti", engine).iloc[0, 0]
    prev_accettati = pd.read_sql("SELECT COUNT(*), COALESCE(SUM(prezzo_totale), 0) FROM public.preventivi WHERE stato IN ('Accettato', 'In lavorazione', 'Completato')", engine)
    prod_lavorazione = pd.read_sql("SELECT COUNT(*) FROM public.preventivi WHERE stato = 'In lavorazione'", engine).iloc[0, 0]
    try:
        incassi_mese = pd.read_sql("""
            SELECT COALESCE(SUM(prezzo_totale), 0) FROM public.preventivi 
            WHERE stato IN ('Accettato', 'In lavorazione', 'Completato') 
            AND DATE_TRUNC('month', data_creazione) = DATE_TRUNC('month', CURRENT_DATE)
        """, engine).iloc[0, 0]
    except Exception:
        incassi_mese = 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Prodotti a Catalogo", prodotti_count)
    c2.metric("Ordini Confermati", prev_accettati.iloc[0, 0], f"{prev_accettati.iloc[0, 1]:,.2f} €")
    c3.metric("In Lavorazione", prod_lavorazione)
    c4.metric("Incassi Mese Corrente", f"{incassi_mese:,.2f} €")

# ---------------------------------------------------------
# 2. AZIENDE
# ---------------------------------------------------------
with tab_aziende:
    st.subheader("Anagrafica Aziende")
    
    col_top1, col_top2 = st.columns([1, 3])
    with col_top1:
        show_add_az = st.button("➕ Nuova Azienda", use_container_width=True)
    with col_top2:
        search_az = st.text_input("🔍 Cerca Azienda (Ragione Sociale, P.IVA, Città, Referente)", key="s_az_single")

    if show_add_az or st.session_state.get("toggle_add_az", False):
        st.session_state["toggle_add_az"] = True
        with st.expander("📝 Form Inserimento Nuova Azienda", expanded=True):
            with st.form("form_nuova_azienda_unica", clear_on_submit=True):
                c_a1, c_a2, c_a3 = st.columns(3)
                rs = c_a1.text_input("Ragione Sociale *")
                piva = c_a2.text_input("Partita IVA")
                email = c_a3.text_input("Email")
                c_a4, c_a5, c_a6 = st.columns(3)
                tel = c_a4.text_input("Telefono")
                sdi = c_a5.text_input("Codice SDI")
                ref = c_a6.text_input("Referente Aziendale")
                c_a7, c_a8, c_a9 = st.columns(3)
                citta = c_a7.text_input("Città")
                provincia = c_a8.text_input("Provincia (es. MI)")
                cap = c_a9.text_input("CAP")

                if st.form_submit_button("💾 Salva Azienda"):
                    if not rs or not rs.strip():
                        st.error("La Ragione Sociale è obbligatoria.")
                    else:
                        with engine.begin() as conn:
                            conn.execute(text("""
                                INSERT INTO public.aziende (ragione_sociale, piva, email, telefono, codice_sdi, referente, citta, provincia, cap)
                                VALUES (:rs, :piva, :email, :tel, :sdi, :ref, :citta, :prov, :cap)
                            """), {
                                "rs": rs.strip(), "piva": (piva or "").strip(), "email": (email or "").strip(),
                                "tel": (tel or "").strip(), "sdi": (sdi or "").strip(), "ref": (ref or "").strip(),
                                "citta": (citta or "").strip(), "prov": (provincia or "").strip(), "cap": (cap or "").strip()
                            })
                        st.success("Azienda salvata!")
                        st.session_state["toggle_add_az"] = False
                        st.cache_data.clear()
                        st.rerun()

    st.markdown("---")
    
    if search_az:
        s_term = f"%{search_az}%"
        df_az = pd.read_sql("""
            SELECT * FROM public.aziende 
            WHERE ragione_sociale ILIKE %(s)s OR piva ILIKE %(s)s OR citta ILIKE %(s)s OR referente ILIKE %(s)s
            ORDER BY ragione_sociale
        """, engine, params={"s": s_term})
    else:
        df_az = load_aziende()

    if df_az.empty:
        st.info("Nessuna azienda trovata.")
    else:
        for _, row in df_az.iterrows():
            c_info, c_actions = st.columns([3, 3])
            
            with c_info:
                loc = f" - {row['citta']} ({row['provincia']})" if row['citta'] else ""
                st.markdown(f"**{row['ragione_sociale']}** | P.IVA: `{row['piva'] or 'N/D'}`{loc}")

            with c_actions:
                col_b1, col_b2, col_b3, col_b4 = st.columns(4)
                
                with col_b1.popover("📄 Info"):
                    st.markdown(f"#### Info: {row['ragione_sociale']}")
                    df_info = pd.DataFrame([{
                        "P.IVA": row['piva'] or '-', "Email": row['email'] or '-', 
                        "Telefono": row['telefono'] or '-', "SDI": row['codice_sdi'] or '-', 
                        "Referente": row['referente'] or '-'
                    }])
                    st.dataframe(df_info, hide_index=True, use_container_width=True)

                with col_b2.popover("📈 Storico"):
                    st.markdown(f"#### Storico Ordini: {row['ragione_sociale']}")
                    
                    y_opt = ["Tutti"] + [str(y) for y in range(2023, 2030)]
                    m_opt = ["Tutti", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
                    
                    cc1, cc2 = st.columns(2)
                    sel_y = cc1.selectbox("Anno", y_opt, key=f"hist_y_{row['id']}")
                    sel_m = cc2.selectbox("Mese", m_opt, key=f"hist_m_{row['id']}")
                    
                    query_storico = """
                        SELECT COUNT(*) as ordini, COALESCE(SUM(prezzo_totale), 0) as totale_euro
                        FROM public.preventivi
                        WHERE azienda_id = %(aid)s AND stato IN ('Accettato', 'In lavorazione', 'Completato')
                    """
                    params_st = {"aid": int(row['id'])}
                    if sel_y != "Tutti":
                        query_storico += " AND EXTRACT(YEAR FROM data_creazione) = %(y)s"
                        params_st["y"] = int(sel_y)
                    if sel_m != "Tutti":
                        query_storico += " AND EXTRACT(MONTH FROM data_creazione) = %(m)s"
                        params_st["m"] = int(sel_m)

                    res_st = pd.read_sql(query_storico, engine, params=params_st)
                    
                    st.metric("Ordini Confermati", res_st.iloc[0]['ordini'])
                    st.metric("Totale Incassato (€)", f"{res_st.iloc[0]['totale_euro']:,.2f} €")

                with col_b3.popover("✏️ Modifica"):
                    st.markdown(f"#### Modifica {row['ragione_sociale']}")
                    with st.form(f"mod_az_{row['id']}", clear_on_submit=True):
                        m_rs = st.text_input("Ragione Sociale", value=row['ragione_sociale'])
                        m_piva = st.text_input("P.IVA", value=row['piva'] or "")
                        m_email = st.text_input("Email", value=row['email'] or "")
                        m_tel = st.text_input("Telefono", value=row['telefono'] or "")
                        m_sdi = st.text_input("SDI", value=row['codice_sdi'] or "")
                        m_ref = st.text_input("Referente", value=row['referente'] or "")
                        m_cit = st.text_input("Città", value=row['citta'] or "")
                        m_pr = st.text_input("Provincia", value=row['provincia'] or "")
                        m_cap = st.text_input("CAP", value=row['cap'] or "")
                        
                        if st.form_submit_button("💾 Salva"):
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    UPDATE public.aziende SET ragione_sociale=:rs, piva=:piva, email=:email, telefono=:tel, 
                                           codice_sdi=:sdi, referente=:ref, citta=:citta, provincia=:pr, cap=:cap
                                    WHERE id=:id
                                """), {
                                    "rs": m_rs.strip(), "piva": m_piva.strip(), "email": m_email.strip(),
                                    "tel": m_tel.strip(), "sdi": m_sdi.strip(), "ref": m_ref.strip(),
                                    "citta": m_cit.strip(), "pr": m_pr.strip(), "cap": m_cap.strip(), "id": int(row['id'])
                                })
                            st.success("Aggiornato!")
                            st.cache_data.clear()
                            st.rerun()

                if col_b4.button("🗑️ Elimina", key=f"del_az_{row['id']}"):
                    with engine.begin() as conn:
                        conn.execute(text("DELETE FROM public.aziende WHERE id=:id"), {"id": int(row['id'])})
                    st.cache_data.clear()
                    st.rerun()
            st.write("")

# ---------------------------------------------------------
# 3. SETTORI E OPERATORI
# ---------------------------------------------------------
with tab_settori_op:
    st.subheader("Gestione Settori & Operatori")
    col_sec, col_op = st.columns(2)

    with col_sec:
        st.markdown("#### 📁 Settori di Produzione")
        with st.form("add_settore_form_new", clear_on_submit=True):
            n_settore = st.text_input("Nome Nuovo Settore")
            if st.form_submit_button("➕ Aggiungi Settore") and n_settore:
                with engine.begin() as conn:
                    conn.execute(text("INSERT INTO public.settori (nome) VALUES (:nome)"), {"nome": n_settore.strip()})
                st.cache_data.clear()
                st.rerun()

        df_settori = load_settori()
        if not df_settori.empty:
            st.dataframe(df_settori, hide_index=True, use_container_width=True)

    with col_op:
        st.markdown("#### 👷 Operatori")
        opts_sett = load_settori()
        with st.form("add_operatore_form_new", clear_on_submit=True):
            n_op = st.text_input("Nome Operatore")
            s_op_name = st.selectbox("Abbina a Settore", opts_sett["nome"].tolist() if not opts_sett.empty else [])
            if st.form_submit_button("➕ Aggiungi Operatore") and n_op and s_op_name:
                s_id_v = opts_sett[opts_sett["nome"] == s_op_name]["id"].values[0]
                with engine.begin() as conn:
                    conn.execute(text("INSERT INTO public.operatori (nome, settore_id) VALUES (:nome, :sid)"), {"nome": n_op.strip(), "sid": int(s_id_v)})
                st.cache_data.clear()
                st.rerun()

        df_op_list = load_operatori()
        if not df_op_list.empty:
            st.dataframe(df_op_list[["operatore", "settore"]], hide_index=True, use_container_width=True)

# ---------------------------------------------------------
# 4. PRODOTTI
# ---------------------------------------------------------
with tab_prodotti:
    st.subheader("Gestione Prodotti")
    
    with st.expander("➕ Inserisci Nuovo Prodotto", expanded=False):
        with st.form("form_add_prod_main", clear_on_submit=True):
            col_p1, col_p2 = st.columns(2)
            p_nome = col_p1.text_input("Nome Prodotto *")
            p_formato = col_p2.text_input("Macchina / Gruppo / Formato")
            p_disegno = col_p1.text_input("Disegno / Codice Schema")
            p_mat = col_p2.text_input("Materiale / Trattamento")
            
            p_note = st.text_area("Note (Opzionale)")

            st.markdown("#### Ore di Lavorazione per Settore")
            settori_db = load_settori()
            ore_settori = {}
            if not settori_db.empty:
                cols_s = st.columns(min(len(settori_db), 4))
                for i, row_s in settori_db.iterrows():
                    with cols_s[i % 4]:
                        ore_settori[row_s['id']] = st.number_input(f"Ore: {row_s['nome']}", min_value=0.0, step=0.5, value=0.0)

            col_c1, col_c2 = st.columns(2)
            costo_int = col_c1.number_input("Costo Interno (€)", min_value=0.0, step=1.0, value=0.0)
            prezzo_ven = col_c2.number_input("Prezzo di Vendita (€)", min_value=0.0, step=1.0, value=0.0)

            if st.form_submit_button("💾 Salva Prodotto"):
                if not p_nome or not p_nome.strip():
                    st.error("Il Nome del Prodotto è obbligatorio.")
                else:
                    with engine.begin() as conn:
                        res = conn.execute(text("""
                            INSERT INTO public.prodotti (nome, macchina_gruppo_formato, disegno, materiale_trattamento, costo_interno, prezzo_vendita, note)
                            VALUES (:nome, :fmt, :dis, :mat, :costo, :prezzo, :note) RETURNING id
                        """), {
                            "nome": p_nome.strip(), "fmt": (p_formato or "").strip(), "dis": (p_disegno or "").strip(),
                            "mat": (p_mat or "").strip(), "costo": float(costo_int), "prezzo": float(prezzo_ven), "note": (p_note or "").strip()
                        })
                        new_p_id = res.fetchone()[0]
                        for s_id, ore_v in ore_settori.items():
                            if ore_v > 0:
                                conn.execute(text("INSERT INTO public.prodotto_ore_settori (prodotto_id, settore_id, ore) VALUES (:pid, :sid, :ore)"),
                                             {"pid": int(new_p_id), "sid": int(s_id), "ore": float(ore_v)})
                    st.success("Prodotto salvato!")
                    st.cache_data.clear()
                    st.rerun()

    st.markdown("### 🔍 Catalogo Prodotti")
    s_prod = st.text_input("Cerca Prodotto", key="search_prod_field")

    if s_prod:
        sp_term = f"%{s_prod}%"
        df_prod_all = pd.read_sql("""
            SELECT * FROM public.prodotti 
            WHERE CAST(id AS TEXT) ILIKE %(s)s OR nome ILIKE %(s)s OR materiale_trattamento ILIKE %(s)s 
            ORDER BY nome
        """, engine, params={"s": sp_term})
    else:
        df_prod_all = load_prodotti()

    if not df_prod_all.empty:
        for _, pr_row in df_prod_all.iterrows():
            cp_info, cp_act = st.columns([4, 2])
            with cp_info:
                st.markdown(f"**#{pr_row['id']} - {pr_row['nome']}** | Prezzo: `{pr_row['prezzo_vendita']:,.2f} €`")
            with cp_act:
                col_pb1, col_pb2, col_pb3 = st.columns(3)
                
                with col_pb1.popover("📄 Dettagli"):
                    df_det_p = pd.DataFrame([{
                        "Formato": pr_row['macchina_gruppo_formato'], "Disegno": pr_row['disegno'],
                        "Materiale": pr_row['materiale_trattamento'], "Note": pr_row['note']
                    }])
                    st.dataframe(df_det_p, hide_index=True, use_container_width=True)

                    df_ore_p = pd.read_sql("""
                        SELECT s.nome as settore, pos.ore FROM public.prodotto_ore_settori pos
                        JOIN public.settori s ON pos.settore_id = s.id WHERE pos.prodotto_id = %(pid)s
                    """, engine, params={"pid": int(pr_row['id'])})
                    st.markdown("**Ore Previste:**")
                    st.dataframe(df_ore_p, hide_index=True, use_container_width=True)

                with col_pb2.popover("✏️ Modifica"):
                    with st.form(f"mod_prod_{pr_row['id']}", clear_on_submit=True):
                        mp_nome = st.text_input("Nome", value=pr_row['nome'])
                        mp_formato = st.text_input("Formato", value=pr_row['macchina_gruppo_formato'] or "")
                        mp_dis = st.text_input("Disegno", value=pr_row['disegno'] or "")
                        mp_mat = st.text_input("Materiale", value=pr_row['materiale_trattamento'] or "")
                        mp_note = st.text_area("Note", value=pr_row['note'] or "")
                        mp_costo = st.number_input("Costo Interno (€)", value=float(pr_row['costo_interno']))
                        mp_prezzo = st.number_input("Prezzo Vendita (€)", value=float(pr_row['prezzo_vendita']))
                        
                        if st.form_submit_button("💾 Salva"):
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    UPDATE public.prodotti SET nome=:n, macchina_gruppo_formato=:fmt, disegno=:d, 
                                           materiale_trattamento=:m, costo_interno=:c, prezzo_vendita=:p, note=:nt
                                    WHERE id=:id
                                """), {"n": mp_nome, "fmt": mp_formato, "d": mp_dis, "m": mp_mat, "c": mp_costo, "p": mp_prezzo, "nt": mp_note, "id": int(pr_row['id'])})
                            st.cache_data.clear()
                            st.rerun()

                if col_pb3.button("🗑️", key=f"del_pr_{pr_row['id']}"):
                    with engine.begin() as conn:
                        conn.execute(text("DELETE FROM public.prodotti WHERE id=:id"), {"id": int(pr_row['id'])})
                    st.cache_data.clear()
                    st.rerun()

# ---------------------------------------------------------
# 5. PREVENTIVI
# ---------------------------------------------------------
with tab_prev:
    st.subheader("Gestione Preventivi")
    pr_tab1, pr_tab2 = st.tabs(["Crea Preventivo", "Lista e Generazione PDF"])

    with pr_tab1:
        az_opts = load_aziende()
        prod_opts = load_prodotti()

        if az_opts.empty or prod_opts.empty:
            st.warning("Devi inserire almeno un'Azienda e un Prodotto prima di poter creare un preventivo.")
        else:
            sel_az_name = st.selectbox("Seleziona Cliente *", az_opts["ragione_sociale"].tolist())
            az_id_selected = az_opts[az_opts["ragione_sociale"] == sel_az_name]["id"].values[0]

            if "cart_preventivo" not in st.session_state:
                st.session_state.cart_preventivo = []

            c_cart1, c_cart2, c_cart3 = st.columns([3, 1, 1])
            sel_p_name = c_cart1.selectbox("Prodotto da Aggiungere", prod_opts["nome"].tolist())
            sel_q = c_cart2.number_input("Quantità", min_value=1, value=1)
            p_data_row = prod_opts[prod_opts["nome"] == sel_p_name].iloc[0]

            if c_cart3.button("➕ Aggiungi al Carrello"):
                st.session_state.cart_preventivo.append({
                    "prodotto_id": int(p_data_row["id"]), "prodotto": sel_p_name,
                    "quantita": int(sel_q), "prezzo_unitario": float(p_data_row["prezzo_vendita"]),
                    "prezzo_totale": float(p_data_row["prezzo_vendita"]) * sel_q
                })
                st.rerun()

            if st.session_state.cart_preventivo:
                df_cart = pd.DataFrame(st.session_state.cart_preventivo)
                st.dataframe(df_cart[["prodotto", "quantita", "prezzo_unitario", "prezzo_totale"]], hide_index=True, use_container_width=True)
                
                tot_prev_val = df_cart['prezzo_totale'].sum()
                st.markdown(f"### Totale Complessivo: `{tot_prev_val:,.2f} €`")

                csav, cclr = st.columns(2)
                if csav.button("💾 Salva Preventivo"):
                    with engine.begin() as conn:
                        res = conn.execute(text("INSERT INTO public.preventivi (azienda_id, prezzo_totale, stato) VALUES (:aid, :tot, 'Bozza') RETURNING id"), 
                                           {"aid": int(az_id_selected), "tot": float(tot_prev_val)})
                        new_prev_id = res.fetchone()[0]
                        for item in st.session_state.cart_preventivo:
                            conn.execute(text("INSERT INTO public.preventivo_dettagli (preventivo_id, prodotto_id, quantita, prezzo_unitario, prezzo_totale) VALUES (:prev_id, :prod_id, :q, :pu, :pt)"), 
                                         {"prev_id": int(new_prev_id), "prod_id": int(item['prodotto_id']), "q": int(item['quantita']), "pu": float(item['prezzo_unitario']), "pt": float(item['prezzo_totale'])})
                    st.session_state.cart_preventivo = []
                    st.success("Salvato!")
                    st.rerun()

                if cclr.button("🗑️ Svuota"):
                    st.session_state.cart_preventivo = []
                    st.rerun()

    with pr_tab2:
        st.markdown("#### 🔍 Filtri Preventivi")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        search_prev = col_s1.text_input("Cerca Numero/Azienda")
        az_df_filt = load_aziende()
        filter_az = col_s2.selectbox("Azienda", ["Tutte"] + (az_df_filt["ragione_sociale"].tolist() if not az_df_filt.empty else []))
        filter_stato = col_s3.selectbox("Stato", ["Tutti", "Bozza", "Accettato", "In lavorazione", "Completato", "Annullato"])
        
        query_prev = "SELECT p.id, a.ragione_sociale, a.citta, a.provincia, a.cap, a.piva, p.prezzo_totale, p.stato, p.data_creazione FROM public.preventivi p JOIN public.aziende a ON p.azienda_id = a.id WHERE 1=1"
        params_p = {}
        if search_prev:
            query_prev += " AND (CAST(p.id AS TEXT) ILIKE %(sp)s OR a.ragione_sociale ILIKE %(sp)s)"
            params_p["sp"] = f"%{search_prev.strip()}%"
        if filter_az != "Tutte":
            query_prev += " AND a.ragione_sociale = %(faz)s"
            params_p["faz"] = filter_az
        if filter_stato != "Tutti":
            query_prev += " AND p.stato = %(fst)s"
            params_p["fst"] = filter_stato

        query_prev += " ORDER BY p.id DESC"
        df_prev_list = pd.read_sql(query_prev, engine, params=params_p)

        for _, r_prev in df_prev_list.iterrows():
            with st.expander(f"Preventivo N. {r_prev['id']} - {r_prev['ragione_sociale']} ({r_prev['prezzo_totale']:,.2f} €) - [{r_prev['stato']}]"):
                c_s1, _ = st.columns([2, 2])
                with c_s1:
                    stati_possibili = ["Bozza", "Accettato", "In lavorazione", "Completato", "Annullato"]
                    nuovo_st = st.selectbox("Cambia Stato", stati_possibili, index=stati_possibili.index(r_prev['stato']), key=f"st_sel_{r_prev['id']}")
                    if st.button("Aggiorna", key=f"btn_upd_st_{r_prev['id']}"):
                        with engine.begin() as conn:
                            conn.execute(text("UPDATE public.preventivi SET stato=:st WHERE id=:id"), {"st": nuovo_st, "id": int(r_prev['id'])})
                        st.rerun()

                # Query corretta: recuperiamo le chiavi esatte che servono al PDF e poi rinominiamo solo per la UI
                df_det = pd.read_sql("""
                    SELECT pr.nome as prodotto, 
                           pd.quantita as quantita, 
                           pd.prezzo_unitario as prezzo_unitario, 
                           pd.prezzo_totale as prezzo_totale 
                    FROM public.preventivo_dettagli pd 
                    JOIN public.prodotti pr ON pd.prodotto_id = pr.id 
                    WHERE pd.preventivo_id = %(pid)s
                """, engine, params={"pid": int(r_prev['id'])})
                
                # Rinominiamo le colonne solo per la visualizzazione sulla pagina web in modo da farle belle
                df_visiva = df_det.rename(columns={
                    'prodotto': 'Prodotto',
                    'quantita': 'Q.tà',
                    'prezzo_unitario': 'Prezzo Unit. (€)',
                    'prezzo_totale': 'Totale (€)'
                })
                st.dataframe(df_visiva, hide_index=True, use_container_width=True)

                pdf_bytes = genera_pdf_preventivo(r_prev['id'], r_prev['ragione_sociale'], r_prev['citta'], r_prev['provincia'], r_prev['cap'], r_prev['piva'], r_prev['data_creazione'].strftime("%d/%m/%Y"), df_det.to_dict('records'), r_prev['prezzo_totale'])
                st.download_button("📄 PDF", data=pdf_bytes, file_name=f"Prev_{r_prev['id']}.pdf", mime="application/pdf", key=f"dl_pdf_{r_prev['id']}")

# ---------------------------------------------------------
# 6. LAVORAZIONE
# ---------------------------------------------------------
with tab_lav:
    st.subheader("Ordini in Lavorazione")
    df_ord_lav = pd.read_sql("SELECT p.id as preventivo_id, a.ragione_sociale, p.prezzo_totale FROM public.preventivi p JOIN public.aziende a ON p.azienda_id = a.id WHERE p.stato = 'In lavorazione' ORDER BY p.id DESC", engine)
    df_all_settori = load_settori()
    df_all_operatori = load_operatori()

    if df_ord_lav.empty:
        st.info("Nessun ordine in lavorazione.")
    else:
        for _, r_lav in df_ord_lav.iterrows():
            p_id = int(r_lav['preventivo_id'])
            col_inf, col_btn1, col_btn2, col_btn3 = st.columns([2.5, 1.2, 1.1, 1.2])
            
            with col_inf:
                st.markdown(f"**Ordine #{p_id}** - {r_lav['ragione_sociale']}")
            
            with col_btn1.popover("⏱️ Registra Ore"):
                df_prod_in_prev = pd.read_sql("SELECT pd.prodotto_id, pr.nome FROM public.preventivo_dettagli pd JOIN public.prodotti pr ON pd.prodotto_id = pr.id WHERE pd.preventivo_id = %(pid)s", engine, params={"pid": p_id})
                if not df_prod_in_prev.empty:
                    with st.form(f"form_reg_ore_{p_id}", clear_on_submit=True):
                        d_lav = st.date_input("Data Lavorazione", value=date.today())
                        sel_prod_name = st.selectbox("Seleziona Prodotto", df_prod_in_prev["nome"].tolist())
                        
                        inputs_ore = {}
                        for _, s_row in df_all_settori.iterrows():
                            s_id = int(s_row['id'])
                            st.markdown(f"**{s_row['nome']}**")
                            ops_s = df_all_operatori[df_all_operatori['settore_id'] == s_id]
                            op_list = ["Nessuno"] + ops_s['operatore'].tolist() if not ops_s.empty else ["Nessuno"]
                            
                            c_op, c_hr = st.columns(2)
                            sel_op = c_op.selectbox("Operatore", op_list, key=f"op_{p_id}_{s_id}")
                            num_hr = c_hr.number_input("Ore", min_value=0.0, step=0.5, value=0.0, key=f"hr_{p_id}_{s_id}")
                            if sel_op != "Nessuno" and num_hr > 0:
                                inputs_ore[s_id] = {"op_id": int(df_all_operatori[df_all_operatori['operatore'] == sel_op]['id'].values[0]), "ore": float(num_hr)}

                        if st.form_submit_button("💾 Salva Ore"):
                            if inputs_ore:
                                sel_prod_id = int(df_prod_in_prev[df_prod_in_prev["nome"] == sel_prod_name]["prodotto_id"].values[0])
                                with engine.begin() as conn:
                                    for sec_id, data_o in inputs_ore.items():
                                        conn.execute(text("INSERT INTO public.ore_lavorate (preventivo_id, prodotto_id, settore_id, operatore_id, data_lavorazione, ore) VALUES (:pid, :prid, :sid, :opid, :dt, :ore)"),
                                                     {"pid": p_id, "prid": sel_prod_id, "sid": sec_id, "opid": data_o['op_id'], "dt": d_lav, "ore": data_o['ore']})
                                st.success("Ore registrate!")
                                st.rerun()

            with col_btn2.popover("📊 Dettaglio"):
                df_det_ore = pd.read_sql("SELECT ol.data_lavorazione as Data, pr.nome as Prodotto, s.nome as Settore, o.nome as Operatore, ol.ore as Ore FROM public.ore_lavorate ol JOIN public.settori s ON ol.settore_id = s.id LEFT JOIN public.prodotti pr ON ol.prodotto_id = pr.id LEFT JOIN public.operatori o ON ol.operatore_id = o.id WHERE ol.preventivo_id = %(pid)s", engine, params={"pid": p_id})
                st.dataframe(df_det_ore, hide_index=True, use_container_width=True)

            with col_btn3:
                if st.button("✅ Completa", key=f"comp_{p_id}"):
                    with engine.begin() as conn:
                        conn.execute(text("UPDATE public.preventivi SET stato = 'Completato' WHERE id = :pid"), {"pid": p_id})
                    st.rerun()

# ---------------------------------------------------------
# 7. REPORT AVANZATO
# ---------------------------------------------------------
with tab_rep:
    st.subheader("Report e Analisi Aziendale")
    
    # 1. Riepilogo Preventivi (Senza Index, Tutti gli stati)
    st.markdown("#### Riepilogo Preventivi per Stato")
    df_rep_raw = pd.read_sql("SELECT stato, COUNT(*) as conteggio, COALESCE(SUM(prezzo_totale), 0) as totale_euro FROM public.preventivi GROUP BY stato", engine)
    stati_completi = pd.DataFrame({"stato": ["Bozza", "Accettato", "In lavorazione", "Completato", "Annullato"]})
    df_rep_final = stati_completi.merge(df_rep_raw, on='stato', how='left').fillna(0)
    df_rep_final.rename(columns={'stato': 'Stato', 'conteggio': 'N. Preventivi', 'totale_euro': 'Totale (€)'}, inplace=True)
    st.dataframe(df_rep_final, hide_index=True, use_container_width=True)

    st.markdown("---")
    
    # 2. Analisi Incassi e Produttività
    st.markdown("### 📈 Analisi Incassi e Produttività (Preventivato vs Effettivo)")
    f_rep1, f_rep2, f_rep3, f_rep4 = st.columns(4)
    
    y_rep_opts = ["Tutti"] + [str(y) for y in range(2023, 2030)]
    m_rep_opts = ["Tutti", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
    
    sel_ry = f_rep1.selectbox("Anno", y_rep_opts, index=0)
    sel_rm = f_rep2.selectbox("Mese", m_rep_opts, index=0)
    
    sec_df = load_settori()
    sec_opts = ["Tutti"] + sec_df['nome'].tolist() if not sec_df.empty else ["Tutti"]
    sel_rsec = f_rep3.selectbox("Settore", sec_opts)
    
    op_df = load_operatori()
    op_opts = ["Tutti"] + op_df['operatore'].tolist() if not op_df.empty else ["Tutti"]
    sel_rop = f_rep4.selectbox("Operatore", op_opts)

    # Base Filter per ordini (Incassi limitati agli ordini Completati nel periodo)
    q_incassi = "SELECT COALESCE(SUM(prezzo_totale), 0) FROM public.preventivi WHERE stato = 'Completato'"
    p_inc = {}
    if sel_ry != "Tutti":
        q_incassi += " AND EXTRACT(YEAR FROM data_creazione) = %(y)s"
        p_inc["y"] = int(sel_ry)
    if sel_rm != "Tutti":
        q_incassi += " AND EXTRACT(MONTH FROM data_creazione) = %(m)s"
        p_inc["m"] = int(sel_rm)
    
    tot_incassi = pd.read_sql(q_incassi, engine, params=p_inc).iloc[0, 0]
    st.metric(f"Totale Incassi Ordini Completati (Periodo Selezionato)", f"{tot_incassi:,.2f} €")

    # Query Produttività (Ore Effettive vs Previste)
    q_ore = """
        SELECT s.nome as Settore, 
               COALESCE(o.nome, 'N/D') as Operatore,
               SUM(ol.ore) as Ore_Effettive
        FROM public.ore_lavorate ol
        JOIN public.settori s ON ol.settore_id = s.id
        LEFT JOIN public.operatori o ON ol.operatore_id = o.id
        WHERE 1=1
    """
    p_ore = {}
    if sel_ry != "Tutti":
        q_ore += " AND EXTRACT(YEAR FROM ol.data_lavorazione) = %(y)s"
        p_ore["y"] = int(sel_ry)
    if sel_rm != "Tutti":
        q_ore += " AND EXTRACT(MONTH FROM ol.data_lavorazione) = %(m)s"
        p_ore["m"] = int(sel_rm)
    if sel_rsec != "Tutti":
        q_ore += " AND s.nome = %(sec)s"
        p_ore["sec"] = sel_rsec
    if sel_rop != "Tutti":
        q_ore += " AND o.nome = %(op)s"
        p_ore["op"] = sel_rop

    q_ore += " GROUP BY s.nome, o.nome ORDER BY s.nome"
    df_produttivita = pd.read_sql(q_ore, engine, params=p_ore)

    if df_produttivita.empty:
        st.info("Nessun dato di lavorazione trovato per i filtri selezionati.")
    else:
        st.markdown("#### Ore Lavorate per Settore e Operatore (nel periodo)")
        st.dataframe(df_produttivita, hide_index=True, use_container_width=True)

# ---------------------------------------------------------
# 8. ASSISTENTE AI
# ---------------------------------------------------------
with tab_ai:
    st.subheader("🤖 Assistente Virtuale AI")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    if prompt := st.chat_input("Come posso aiutarti?"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            if client:
                try:
                    ans = client.models.generate_content(model='gemini-2.5-flash', contents=prompt).text
                    st.markdown(ans)
                    st.session_state.chat_history.append({"role": "assistant", "content": ans})
                except Exception as e:
                    st.error(f"Errore AI: {e}")
            else:
                st.warning("API Key Gemini mancante.")
