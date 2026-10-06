import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
from google import genai
from google.genai import types
from database import init_db, get_connection

# Configurazione Pagina
st.set_page_config(
    page_title="Lupone Enterprise",
    page_icon="🟢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inizializzazione Database e Verifica Schema
try:
    init_db()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE public.aziende ADD COLUMN IF NOT EXISTS citta TEXT;")
            cur.execute("ALTER TABLE public.aziende ADD COLUMN IF NOT EXISTS provincia TEXT;")
            cur.execute("ALTER TABLE public.aziende ADD COLUMN IF NOT EXISTS cap TEXT;")
            conn.commit()
except Exception as e:
    st.error(f"Errore nell'inizializzazione del database: {e}")

# =========================================================
# STILE GRAFICO PERSONALIZZATO
# =========================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
        background-color: #F8F9FA !important;
        color: #111827 !important;
    }

    #MainMenu, footer, header { visibility: hidden; }

    h1, h2, h3 {
        color: #111827 !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }

    .brand-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 0px 20px 0px;
        border-bottom: 1px solid #E5E7EB;
        margin-bottom: 20px;
    }
    .brand-logo-title {
        display: flex;
        align-items: center;
        gap: 12px;
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
        font-size: 14px !important;
        padding: 0 4px !important;
    }

    .stTabs [aria-selected="true"] {
        color: #0B3C2D !important;
        font-weight: 700 !important;
        border-bottom-color: #0B3C2D !important;
    }

    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
    }

    div[data-testid="stMetric"] label {
        color: #6B7280 !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
    }

    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #111827 !important;
        font-size: 28px !important;
        font-weight: 700 !important;
    }

    .alert-banner {
        background-color: #FFFDF0;
        border: 1px solid #FDE68A;
        border-radius: 10px;
        padding: 14px 20px;
        margin: 16px 0px;
    }
    .alert-banner-text {
        color: #92400E;
        font-size: 14px;
        font-weight: 600;
    }

    .stButton > button, div[data-testid="stFormSubmitButton"] > button {
        background-color: #0B3C2D !important;
        color: #FFFFFF !important;
        border: 1px solid #0B3C2D !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 6px 14px !important;
    }

    .stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #07291F !important;
        border-color: #07291F !important;
    }

    .action-card {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
</style>
""", unsafe_allow_html=True)

# Generator PDF Professionale
def genera_pdf_preventivo(id_preventivo, ragione_sociale, citta, provincia, cap, piva, data, articoli, totale):
    pdf = FPDF()
    pdf.add_page()
    
    # Intestazione Fornitore (Sinistra)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.set_text_color(11, 60, 45)
    pdf.cell(100, 6, "GESTIONALE LUPONE S.R.L.", ln=False)
    
    # Spett.le Cliente (Destra)
    pdf.set_font("Helvetica", 'B', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(90, 5, "Spett.le Cliente:", ln=True, align='R')
    
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(100, 5, "Via dell'Industria, 45 - 20100 Milano (MI)", ln=False)
    
    # Ragione Sociale Cliente Destra
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
    
    # Titolo Preventivo
    pdf.set_font("Helvetica", 'B', 14)
    pdf.set_text_color(11, 60, 45)
    pdf.cell(0, 8, f"OFFERTA PREVENTIVO N. {id_preventivo} DEL {data}", ln=True)
    
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(70, 70, 70)
    pdf.multi_cell(0, 5, "Con la presente Vi inviamo la nostra migliore offerta commerciale per i prodotti/servizi sotto specificati:")
    pdf.ln(4)
    
    # Tabella Prodotti
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
        pdf.cell(35, 8, f"{art['prezzo_unitario']:,.2f}", border=1, align='R', fill=True)
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

# Gemini Client
@st.cache_resource
def get_gemini_client():
    api_key = st.secrets.get("GEMINI_API_KEY")
    return genai.Client(api_key=api_key) if api_key else None

client = get_gemini_client()

# Header
st.markdown("""
<div class="brand-header">
    <div class="brand-logo-title">
        <div class="brand-icon">🟢</div>
        <div>
            <div style="font-weight: 700; font-size: 18px; color: #111827;">GESTIONALE ENTERPRISE</div>
            <div style="font-size: 12px; color: #6B7280;">Piattaforma di Gestione Aziendale e Ordini</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Tab principali
tab_dash, tab_aziende, tab_settori_op, tab_prodotti, tab_prev, tab_lav, tab_rep, tab_ai = st.tabs([
    "Panoramica", "Aziende", "Settori & Operatori",
    "Prodotti", "Preventivi", "Lavorazione",
    "Report", "Assistente AI"
])

# ---------------------------------------------------------
# 1. PANORAMICA
# ---------------------------------------------------------
with tab_dash:
    st.subheader("Panoramica")
    with get_connection() as conn:
        prodotti_count = pd.read_sql("SELECT COUNT(*) FROM public.prodotti", conn).iloc[0, 0]
        prev_accettati = pd.read_sql("SELECT COUNT(*), COALESCE(SUM(prezzo_totale), 0) FROM public.preventivi WHERE stato IN ('In lavorazione', 'Completato')", conn)
        prod_lavorazione = pd.read_sql("SELECT COUNT(*) FROM public.preventivi WHERE stato = 'In lavorazione'", conn).iloc[0, 0]
        try:
            incassi_mese = pd.read_sql("""
                SELECT COALESCE(SUM(prezzo_totale), 0) FROM public.preventivi 
                WHERE stato IN ('In lavorazione', 'Completato') 
                AND DATE_TRUNC('month', data_creazione) = DATE_TRUNC('month', CURRENT_DATE)
            """, conn).iloc[0, 0]
        except Exception:
            incassi_mese = 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Prodotti a Catalogo", prodotti_count)
    c2.metric("Preventivi Approvati", prev_accettati.iloc[0, 0], f"{prev_accettati.iloc[0, 1]:,.2f} €")
    c3.metric("Ordini in Lavorazione", prod_lavorazione)
    c4.metric("Incassi Mese Corrente", f"{incassi_mese:,.2f} €")

    st.markdown(f"""
    <div class="alert-banner">
        <span class="alert-banner-text">⚠ Attenzione: Ci sono {prod_lavorazione} ordini attualmente in lavorazione.</span>
    </div>
    """, unsafe_allow_html=True)

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

                b_sub, b_close = st.columns([1, 1])
                if b_sub.form_submit_button("💾 Salva Azienda"):
                    if not rs or not rs.strip():
                        st.error("La Ragione Sociale è obbligatoria.")
                    else:
                        with get_connection() as conn:
                            with conn.cursor() as cur:
                                cur.execute("""
                                    INSERT INTO public.aziende (ragione_sociale, piva, email, telefono, codice_sdi, referente, citta, provincia, cap)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """, (rs.strip(), (piva or "").strip(), (email or "").strip(), (tel or "").strip(), 
                                      (sdi or "").strip(), (ref or "").strip(), (citta or "").strip(), (provincia or "").strip(), (cap or "").strip()))
                                conn.commit()
                        st.success("Azienda salvata!")
                        st.session_state["toggle_add_az"] = False
                        st.rerun()

    st.markdown("---")
    st.markdown("### Elenco Aziende Registrate")

    with get_connection() as conn:
        if search_az:
            s_term = f"%{search_az}%"
            df_az = pd.read_sql("""
                SELECT * FROM public.aziende 
                WHERE ragione_sociale ILIKE %s OR piva ILIKE %s OR citta ILIKE %s OR referente ILIKE %s
                ORDER BY ragione_sociale
            """, conn, params=(s_term, s_term, s_term, s_term))
        else:
            df_az = pd.read_sql("SELECT * FROM public.aziende ORDER BY ragione_sociale", conn)

    if df_az.empty:
        st.info("Nessuna azienda trovata.")
    else:
        for _, row in df_az.iterrows():
            c_info, c_actions = st.columns([4, 2])
            
            with c_info:
                loc = f" - {row['citta']} ({row['provincia']})" if row['citta'] else ""
                st.markdown(f"**{row['ragione_sociale']}** | P.IVA: `{row['piva'] or 'N/D'}`{loc}")

            with c_actions:
                col_b1, col_b2, col_b3 = st.columns(3)
                
                with col_b1.popover("🔍"):
                    st.markdown(f"#### Dettagli: {row['ragione_sociale']}")
                    st.write(f"**P.IVA:** {row['piva'] or 'N/D'}")
                    st.write(f"**Email:** {row['email'] or 'N/D'}")
                    st.write(f"**Telefono:** {row['telefono'] or 'N/D'}")
                    st.write(f"**Codice SDI:** {row['codice_sdi'] or 'N/D'}")
                    st.write(f"**Referente:** {row['referente'] or 'N/D'}")
                    st.write(f"**Indirizzo:** {row['citta'] or ''} ({row['provincia'] or ''}) {row['cap'] or ''}")

                with col_b2.popover("✏️"):
                    st.markdown(f"#### Modifica {row['ragione_sociale']}")
                    with st.form(f"mod_az_{row['id']}"):
                        m_rs = st.text_input("Ragione Sociale", value=row['ragione_sociale'])
                        m_piva = st.text_input("P.IVA", value=row['piva'] or "")
                        m_email = st.text_input("Email", value=row['email'] or "")
                        m_tel = st.text_input("Telefono", value=row['telefono'] or "")
                        m_sdi = st.text_input("SDI", value=row['codice_sdi'] or "")
                        m_ref = st.text_input("Referente", value=row['referente'] or "")
                        m_cit = st.text_input("Città", value=row['citta'] or "")
                        m_pr = st.text_input("Provincia", value=row['provincia'] or "")
                        m_cap = st.text_input("CAP", value=row['cap'] or "")
                        
                        if st.form_submit_button("💾 Salva Modifiche"):
                            with get_connection() as conn:
                                with conn.cursor() as cur:
                                    cur.execute("""
                                        UPDATE public.aziende SET ragione_sociale=%s, piva=%s, email=%s, telefono=%s, codice_sdi=%s, referente=%s, citta=%s, provincia=%s, cap=%s
                                        WHERE id=%s
                                    """, (m_rs.strip(), m_piva.strip(), m_email.strip(), m_tel.strip(), m_sdi.strip(), m_ref.strip(), m_cit.strip(), m_pr.strip(), m_cap.strip(), int(row['id'])))
                                    conn.commit()
                            st.success("Azienda aggiornata!")
                            st.rerun()

                if col_b3.button("🗑️", key=f"del_az_{row['id']}"):
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("DELETE FROM public.aziende WHERE id=%s", (int(row['id']),))
                            conn.commit()
                    st.warning("Azienda eliminata!")
                    st.rerun()

# ---------------------------------------------------------
# 3. SETTORI & OPERATORI
# ---------------------------------------------------------
with tab_settori_op:
    st.subheader("Gestione Settori & Operatori")
    col_sec, col_op = st.columns(2)

    with col_sec:
        st.markdown("#### 📁 Settori di Produzione")
        with st.form("add_settore_form_new", clear_on_submit=True):
            n_settore = st.text_input("Nome Nuovo Settore")
            if st.form_submit_button("➕ Aggiungi Settore") and n_settore:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("INSERT INTO public.settori (nome) VALUES (%s)", (n_settore.strip(),))
                        conn.commit()
                st.success("Settore creato!")
                st.rerun()

        with get_connection() as conn:
            df_settori = pd.read_sql("SELECT * FROM public.settori ORDER BY nome", conn)

        st.markdown("##### Elenco Settori")
        for _, s_row in df_settori.iterrows():
            cs_text, cs_btn1, cs_btn2 = st.columns([3, 1, 1])
            cs_text.write(f"• **{s_row['nome']}**")
            
            with cs_btn1.popover("✏️"):
                with st.form(f"mod_sec_{s_row['id']}"):
                    edit_s_name = st.text_input("Nome Settore", value=s_row['nome'])
                    if st.form_submit_button("Salva"):
                        with get_connection() as conn:
                            with conn.cursor() as cur:
                                cur.execute("UPDATE public.settori SET nome=%s WHERE id=%s", (edit_s_name.strip(), int(s_row['id'])))
                                conn.commit()
                        st.rerun()

            if cs_btn2.button("🗑️", key=f"del_sec_{s_row['id']}"):
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM public.settori WHERE id=%s", (int(s_row['id']),))
                        conn.commit()
                st.rerun()

    with col_op:
        st.markdown("#### 👷 Operatori")
        with get_connection() as conn:
            opts_sett = pd.read_sql("SELECT id, nome FROM public.settori ORDER BY nome", conn)

        with st.form("add_operatore_form_new", clear_on_submit=True):
            n_op = st.text_input("Nome Operatore")
            s_op_name = st.selectbox("Abbina a Settore", opts_sett["nome"].tolist() if not opts_sett.empty else [])
            
            if st.form_submit_button("➕ Aggiungi Operatore") and n_op and s_op_name:
                s_id_v = opts_sett[opts_sett["nome"] == s_op_name]["id"].values[0]
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("INSERT INTO public.operatori (nome, settore_id) VALUES (%s, %s)", (n_op.strip(), int(s_id_v)))
                        conn.commit()
                st.success("Operatore aggiunto!")
                st.rerun()

        with get_connection() as conn:
            df_op_list = pd.read_sql("""
                SELECT o.id, o.nome as operatore, s.nome as settore, o.settore_id
                FROM public.operatori o LEFT JOIN public.settori s ON o.settore_id = s.id
                ORDER BY o.nome
            """, conn)

        st.markdown("##### Elenco Operatori")
        for _, o_row in df_op_list.iterrows():
            co_text, co_btn1, co_btn2 = st.columns([3, 1, 1])
            co_text.write(f"• **{o_row['operatore']}** ({o_row['settore'] or 'Nessun Settore'})")
            
            with co_btn1.popover("✏️"):
                with st.form(f"mod_op_{o_row['id']}"):
                    edit_o_name = st.text_input("Nome Operatore", value=o_row['operatore'])
                    edit_o_sec = st.selectbox("Settore", opts_sett["nome"].tolist() if not opts_sett.empty else [], 
                                              index=opts_sett["nome"].tolist().index(o_row['settore']) if o_row['settore'] in opts_sett["nome"].tolist() else 0)
                    if st.form_submit_button("Salva"):
                        new_s_id = opts_sett[opts_sett["nome"] == edit_o_sec]["id"].values[0]
                        with get_connection() as conn:
                            with conn.cursor() as cur:
                                cur.execute("UPDATE public.operatori SET nome=%s, settore_id=%s WHERE id=%s", (edit_o_name.strip(), int(new_s_id), int(o_row['id'])))
                                conn.commit()
                        st.rerun()

            if co_btn2.button("🗑", key=f"del_op_{o_row['id']}"):
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM public.operatori WHERE id=%s", (int(o_row['id']),))
                        conn.commit()
                st.rerun()

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

            st.markdown("#### Ore di Lavorazione per Settore")
            with get_connection() as conn:
                settori_db = pd.read_sql("SELECT * FROM public.settori", conn)
            
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
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                INSERT INTO public.prodotti (nome, macchina_gruppo_formato, disegno, materiale_trattamento, costo_interno, prezzo_vendita)
                                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                            """, (p_nome.strip(), (p_formato or "").strip(), (p_disegno or "").strip(), (p_mat or "").strip(), float(costo_int), float(prezzo_ven)))
                            new_p_id = cur.fetchone()[0]

                            for s_id, ore_v in ore_settori.items():
                                if ore_v > 0:
                                    cur.execute("INSERT INTO public.prodotto_ore_settori (prodotto_id, settore_id, ore) VALUES (%s, %s, %s)", (int(new_p_id), int(s_id), float(ore_v)))
                            conn.commit()
                    st.success("Prodotto salvato!")
                    st.rerun()

    st.markdown("---")
    st.markdown("### 🔍 Ricerca e Catalogo Prodotti")
    s_prod = st.text_input("Cerca Prodotto (per ID, Nome, Materiale, Disegno, Formato)", key="search_prod_field")

    with get_connection() as conn:
        if s_prod:
            sp_term = f"%{s_prod}%"
            df_prod_all = pd.read_sql("""
                SELECT * FROM public.prodotti 
                WHERE CAST(id AS TEXT) ILIKE %s OR nome ILIKE %s OR materiale_trattamento ILIKE %s OR disegno ILIKE %s OR macchina_gruppo_formato ILIKE %s
                ORDER BY nome
            """, conn, params=(sp_term, sp_term, sp_term, sp_term, sp_term))
        else:
            df_prod_all = pd.read_sql("SELECT * FROM public.prodotti ORDER BY nome", conn)

    if df_prod_all.empty:
        st.info("Nessun prodotto trovato.")
    else:
        for _, pr_row in df_prod_all.iterrows():
            cp_info, cp_act = st.columns([4, 2])
            
            with cp_info:
                st.markdown(f"**#{pr_row['id']} - {pr_row['nome']}** | Formato: `{pr_row['macchina_gruppo_formato'] or 'N/D'}` | Disegno: `{pr_row['disegno'] or 'N/D'}` | Prezzo: `{pr_row['prezzo_vendita']:,.2f} €`")

            with cp_act:
                col_pb1, col_pb2, col_pb3 = st.columns(3)
                
                with col_pb1.popover("🔍"):
                    st.markdown(f"#### Dettagli Prodotto #{pr_row['id']}")
                    st.write(f"**Nome:** {pr_row['nome']}")
                    st.write(f"**Formato:** {pr_row['macchina_gruppo_formato'] or 'N/D'}")
                    st.write(f"**Disegno:** {pr_row['disegno'] or 'N/D'}")
                    st.write(f"**Materiale:** {pr_row['materiale_trattamento'] or 'N/D'}")
                    st.write(f"**Costo Interno:** {pr_row['costo_interno']:,.2f} €")
                    st.write(f"**Prezzo Vendita:** {pr_row['prezzo_vendita']:,.2f} €")
                    
                    with get_connection() as conn:
                        df_ore_p = pd.read_sql("""
                            SELECT s.nome as settore, pos.ore FROM public.prodotto_ore_settori pos
                            JOIN public.settori s ON pos.settore_id = s.id WHERE pos.prodotto_id = %s
                        """, conn, params=(int(pr_row['id']),))
                    st.markdown("**Ore Previste per Settore:**")
                    st.dataframe(df_ore_p, use_container_width=True)

                with col_pb2.popover("✏️"):
                    st.markdown(f"#### Modifica #{pr_row['id']}")
                    with st.form(f"mod_prod_form_{pr_row['id']}"):
                        mp_nome = st.text_input("Nome", value=pr_row['nome'])
                        mp_formato = st.text_input("Formato", value=pr_row['macchina_gruppo_formato'] or "")
                        mp_dis = st.text_input("Disegno", value=pr_row['disegno'] or "")
                        mp_mat = st.text_input("Materiale", value=pr_row['materiale_trattamento'] or "")
                        mp_costo = st.number_input("Costo Interno (€)", value=float(pr_row['costo_interno']))
                        mp_prezzo = st.number_input("Prezzo Vendita (€)", value=float(pr_row['prezzo_vendita']))
                        
                        if st.form_submit_button("Salva"):
                            with get_connection() as conn:
                                with conn.cursor() as cur:
                                    cur.execute("""
                                        UPDATE public.prodotti SET nome=%s, macchina_gruppo_formato=%s, disegno=%s, materiale_trattamento=%s, costo_interno=%s, prezzo_vendita=%s
                                        WHERE id=%s
                                    """, (mp_nome.strip(), mp_formato.strip(), mp_dis.strip(), mp_mat.strip(), float(mp_costo), float(mp_prezzo), int(pr_row['id'])))
                                    conn.commit()
                            st.rerun()

                if col_pb3.button("🗑️", key=f"del_pr_{pr_row['id']}"):
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("DELETE FROM public.prodotti WHERE id=%s", (int(pr_row['id']),))
                            conn.commit()
                    st.rerun()

# ---------------------------------------------------------
# 5. PREVENTIVI
# ---------------------------------------------------------
with tab_prev:
    st.subheader("Gestione Preventivi")
    pr_tab1, pr_tab2 = st.tabs(["Crea Preventivo", "Lista e Generazione PDF"])

    with pr_tab1:
        with get_connection() as conn:
            az_opts = pd.read_sql("SELECT id, ragione_sociale FROM public.aziende ORDER BY ragione_sociale", conn)
            prod_opts = pd.read_sql("SELECT id, nome, prezzo_vendita FROM public.prodotti ORDER BY nome", conn)

        if az_opts.empty or prod_opts.empty:
            st.warning("Devi inserire almeno un'Azienda e un Prodotto prima di poter creare un preventivo.")
        else:
            sel_az_name = st.selectbox("Seleziona Cliente *", az_opts["ragione_sociale"].tolist())
            az_id_selected = az_opts[az_opts["ragione_sociale"] == sel_az_name]["id"].values[0]

            st.markdown("#### Aggiungi Articoli al Preventivo")
            if "cart_preventivo" not in st.session_state:
                st.session_state.cart_preventivo = []

            c_cart1, c_cart2, c_cart3 = st.columns([3, 1, 1])
            sel_p_name = c_cart1.selectbox("Prodotto da Aggiungere", prod_opts["nome"].tolist())
            sel_q = c_cart2.number_input("Quantità", min_value=1, value=1)
            p_data_row = prod_opts[prod_opts["nome"] == sel_p_name].iloc[0]

            if c_cart3.button("➕ Aggiungi al Carrello"):
                st.session_state.cart_preventivo.append({
                    "prodotto_id": int(p_data_row["id"]),
                    "prodotto": sel_p_name,
                    "quantita": int(sel_q),
                    "prezzo_unitario": float(p_data_row["prezzo_vendita"]),
                    "prezzo_totale": float(p_data_row["prezzo_vendita"]) * sel_q
                })
                st.success("Articolo aggiunto!")

            if st.session_state.cart_preventivo:
                st.markdown("##### Articoli Inseriti:")
                tot_prev_val = 0.0
                
                for idx, item in enumerate(st.session_state.cart_preventivo):
                    ci1, ci2, ci3, ci4, ci5 = st.columns([3, 1, 1, 1, 1])
                    ci1.write(f"**{item['prodotto']}**")
                    ci2.write(f"Q.tà: {item['quantita']}")
                    ci3.write(f"{item['prezzo_unitario']:,.2f} €")
                    ci4.write(f"**{item['prezzo_totale']:,.2f} €**")
                    tot_prev_val += item['prezzo_totale']
                    
                    if ci5.button("❌", key=f"del_cart_{idx}"):
                        st.session_state.cart_preventivo.pop(idx)
                        st.rerun()

                st.markdown(f"### Totale Complessivo: `{tot_prev_val:,.2f} €`")

                csav, cclr = st.columns(2)
                if csav.button("💾 Salva e Conferma Preventivo"):
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                INSERT INTO public.preventivi (azienda_id, prezzo_totale, stato, data_creazione)
                                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                                RETURNING id
                            """, (int(az_id_selected), float(tot_prev_val), 'Bozza'))
                            new_prev_id = cur.fetchone()[0]

                            for item in st.session_state.cart_preventivo:
                                cur.execute("""
                                    INSERT INTO public.preventivo_dettagli (preventivo_id, prodotto_id, quantita, prezzo_unitario, prezzo_totale)
                                    VALUES (%s, %s, %s, %s, %s)
                                """, (int(new_prev_id), int(item['prodotto_id']), int(item['quantita']), float(item['prezzo_unitario']), float(item['prezzo_totale'])))

                            conn.commit()
                    st.session_state.cart_preventivo = []
                    st.success(f"Preventivo N. {new_prev_id} salvato con successo!")
                    st.rerun()

                if cclr.button("🗑️ Svuota Carrello"):
                    st.session_state.cart_preventivo = []
                    st.rerun()

    with pr_tab2:
        st.markdown("### Elenco Preventivi")
        with get_connection() as conn:
            df_prev_list = pd.read_sql("""
                SELECT p.id, a.ragione_sociale, a.citta, a.provincia, a.cap, a.piva,
                       p.prezzo_totale, p.stato, p.data_creazione
                FROM public.preventivi p
                JOIN public.aziende a ON p.azienda_id = a.id
                ORDER BY p.id DESC
            """, conn)

        if df_prev_list.empty:
            st.info("Nessun preventivo registrato.")
        else:
            for _, r_prev in df_prev_list.iterrows():
                with st.expander(f"Preventivo N. {r_prev['id']} - {r_prev['ragione_sociale']} ({r_prev['prezzo_totale']:,.2f} €) - [{r_prev['stato']}]"):
                    c_s1, c_s2 = st.columns([2, 2])
                    
                    with c_s1:
                        stati_possibili = ["Bozza", "In lavorazione", "Completato", "Annullato"]
                        idx_st = stati_possibili.index(r_prev['stato']) if r_prev['stato'] in stati_possibili else 0
                        nuovo_st = st.selectbox("Stato Preventivo", stati_possibili, index=idx_st, key=f"st_sel_{r_prev['id']}")
                        
                        if st.button("Aggiorna Stato", key=f"btn_upd_st_{r_prev['id']}"):
                            with get_connection() as conn:
                                with conn.cursor() as cur:
                                    cur.execute("UPDATE public.preventivi SET stato=%s WHERE id=%s", (nuovo_st, int(r_prev['id'])))
                                    conn.commit()
                            st.success("Stato aggiornato!")
                            st.rerun()

                    with get_connection() as conn:
                        df_det = pd.read_sql("""
                            SELECT pd.*, pr.nome as prodotto
                            FROM public.preventivo_dettagli pd
                            JOIN public.prodotti pr ON pd.prodotto_id = pr.id
                            WHERE pd.preventivo_id = %s
                        """, conn, params=(int(r_prev['id']),))

                    st.markdown("**Dettaglio Articoli:**")
                    st.dataframe(df_det[["prodotto", "quantita", "prezzo_unitario", "prezzo_totale"]], use_container_width=True)

                    data_str = r_prev['data_creazione'].strftime("%d/%m/%Y") if pd.notnull(r_prev['data_creazione']) else datetime.now().strftime("%d/%m/%Y")
                    pdf_bytes = genera_pdf_preventivo(
                        id_preventivo=r_prev['id'],
                        ragione_sociale=r_prev['ragione_sociale'],
                        citta=r_prev['citta'],
                        provincia=r_prev['provincia'],
                        cap=r_prev['cap'],
                        piva=r_prev['piva'],
                        data=data_str,
                        articoli=df_det.to_dict('records'),
                        totale=r_prev['prezzo_totale']
                    )

                    st.download_button(
                        label="📄 Scarica PDF Preventivo",
                        data=pdf_bytes,
                        file_name=f"Preventivo_{r_prev['id']}_{r_prev['ragione_sociale']}.pdf",
                        mime="application/pdf",
                        key=f"dl_pdf_btn_{r_prev['id']}"
                    )

# ---------------------------------------------------------
# 6. LAVORAZIONE
# ---------------------------------------------------------
with tab_lav:
    st.subheader("Ordini in Lavorazione")
    with get_connection() as conn:
        df_ord_lav = pd.read_sql("""
            SELECT p.id as preventivo_id, a.ragione_sociale, p.prezzo_totale, p.data_creazione
            FROM public.preventivi p
            JOIN public.aziende a ON p.azienda_id = a.id
            WHERE p.stato = 'In lavorazione'
            ORDER BY p.id DESC
        """, conn)

    if df_ord_lav.empty:
        st.info("Nessun ordine in stato 'In lavorazione'.")
    else:
        for _, r_lav in df_ord_lav.iterrows():
            with st.container():
                st.markdown(f"### Ordine #{r_lav['preventivo_id']} - {r_lav['ragione_sociale']}")
                st.caption(f"Valore: {r_lav['prezzo_totale']:,.2f} € | Data: {r_lav['data_creazione']}")
                
                with get_connection() as conn:
                    df_det_lav = pd.read_sql("""
                        SELECT pr.nome as prodotto, pd.quantita, pr.id as prodotto_id
                        FROM public.preventivo_dettagli pd
                        JOIN public.prodotti pr ON pd.prodotto_id = pr.id
                        WHERE pd.preventivo_id = %s
                    """, conn, params=(int(r_lav['preventivo_id']),))

                st.dataframe(df_det_lav[["prodotto", "quantita"]], use_container_width=True)
                st.markdown("---")

# ---------------------------------------------------------
# 7. REPORT
# ---------------------------------------------------------
with tab_rep:
    st.subheader("Report e Analisi")
    with get_connection() as conn:
        df_rep = pd.read_sql("""
            SELECT stato, COUNT(*) as conteggio, COALESCE(SUM(prezzo_totale), 0) as totale_euro
            FROM public.preventivi
            GROUP BY stato
        """, conn)

    if df_rep.empty:
        st.info("Nessun dato disponibile per i report.")
    else:
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.markdown("#### Preventivi per Stato")
            st.dataframe(df_rep, use_container_width=True)
        with col_r2:
            st.markdown("#### Totale Euro per Stato")
            st.bar_chart(df_rep.set_index('stato')['totale_euro'])

# ---------------------------------------------------------
# 8. ASSISTENTE AI
# ---------------------------------------------------------
with tab_ai:
    st.subheader("🤖 Assistente Virtuale AI")
    st.caption("Fai domande sulla gestione, analizza preventivi o chiedi consigli strategici.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Come posso aiutarti con la gestione aziendale?"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if client:
                try:
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt
                    )
                    ans = response.text
                    st.markdown(ans)
                    st.session_state.chat_history.append({"role": "assistant", "content": ans})
                except Exception as e:
                    st.error(f"Errore nella chiamata a Gemini: {e}")
            else:
                st.warning("Chiave `GEMINI_API_KEY` non configurata nei secrets di Streamlit.")
