import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
from google import genai
from google.genai import types
from database import init_db, get_connection

# Configurazione Pagina
st.set_page_config(
    page_title="Enterprise ERP System",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inizializzazione Database e Migrazioni Schema
try:
    init_db()
except Exception as e:
    st.error(f"Errore nell'inizializzazione del database: {e}")

# Styling Personalizzato
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    h1, h2, h3 { color: #1a252f; font-weight: 600; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e9ecef;
        padding: 18px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.03);
    }
    div[data-testid="stMetric"] label { color: #6c757d !important; font-weight: 500; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px; background-color: #ffffff; padding: 8px; border-radius: 10px; border: 1px solid #e9ecef;
    }
    .stTabs [data-baseweb="tab"] { height: 45px; border-radius: 8px; font-weight: 500; color: #495057; }
    .stTabs [aria-selected="true"] { background-color: #0d6efd !important; color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

# Generator PDF senza problemi di Encoding/Euro
def genera_pdf_preventivo(id_preventivo, ragione_sociale, data, articoli, totale):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 18)
    pdf.cell(0, 10, f"PREVENTIVO N. #{id_preventivo}", ln=True, align='C')
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 10, f"Data: {data} | Cliente: {ragione_sociale}", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(80, 8, "Prodotto", border=1)
    pdf.cell(30, 8, "Quantita", border=1, align='C')
    pdf.cell(40, 8, "Prezzo Unit. (EUR)", border=1, align='R')
    pdf.cell(40, 8, "Prezzo Tot. (EUR)", border=1, align='R')
    pdf.ln()

    pdf.set_font("Helvetica", size=10)
    for art in articoli:
        pdf.cell(80, 8, str(art['prodotto'])[:35], border=1)
        pdf.cell(30, 8, str(art['quantita']), border=1, align='C')
        pdf.cell(40, 8, f"{art['prezzo_unitario']:.2f} EUR", border=1, align='R')
        pdf.cell(40, 8, f"{art['prezzo_totale']:.2f} EUR", border=1, align='R')
        pdf.ln()

    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(150, 10, "TOTALE PREVENTIVO:", align='R')
    pdf.cell(40, 10, f"{totale:.2f} EUR", align='R')
    
    output_str = pdf.output(dest='S')
    return output_str.encode('latin1') if isinstance(output_str, str) else bytes(output_str)

# Inizializzazione Client Gemini
@st.cache_resource
def get_gemini_client():
    api_key = st.secrets.get("GEMINI_API_KEY")
    return genai.Client(api_key=api_key) if api_key else None

client = get_gemini_client()

st.title("🏢 Gestione Aziendale Enterprise")

tab_dash, tab_aziende, tab_settori_op, tab_prodotti, tab_prev, tab_lav, tab_rep, tab_ai = st.tabs([
    "📊 Dashboard", "🏢 Aziende", "⚙️️ Settori e Operatori",
    "📦 Prodotti", "📄 Preventivi", "🛠️ Lavorazione",
    "📈 Report", "🤖 Assistente AI"
])

# ---------------------------------------------------------
# 1. DASHBOARD
# ---------------------------------------------------------
with tab_dash:
    st.header("📊 Panoramica Generale")
    
    with get_connection() as conn:
        prodotti_count = pd.read_sql("SELECT COUNT(*) FROM prodotti", conn).iloc[0, 0]
        prev_accettati = pd.read_sql("SELECT COUNT(*), COALESCE(SUM(prezzo_totale), 0) FROM preventivi WHERE stato = 'In lavorazione' OR stato = 'Completato'", conn)
        prod_lavorazione = pd.read_sql("SELECT COUNT(*) FROM preventivi WHERE stato = 'In lavorazione'", conn).iloc[0, 0]
        
        # Gestione sicura per incassi del mese corrente
        try:
            incassi_mese = pd.read_sql("""
                SELECT COALESCE(SUM(prezzo_totale), 0) FROM preventivi 
                WHERE (stato = 'In lavorazione' OR stato = 'Completato') 
                AND DATE_TRUNC('month', data_creazione) = DATE_TRUNC('month', CURRENT_DATE)
            """, conn).iloc[0, 0]
        except Exception:
            incassi_mese = 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Prodotti a Catalogo", prodotti_count)
    c2.metric("Preventivi Approvati", prev_accettati.iloc[0, 0], f"{prev_accettati.iloc[0, 1]:,.2f} €")
    c3.metric("Ordini in Lavorazione", prod_lavorazione)
    c4.metric("Incassi Mese Corrente", f"{incassi_mese:,.2f} €")

    st.markdown("---")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("Stato Preventivi")
        with get_connection() as conn:
            df_stati = pd.read_sql("SELECT stato, COUNT(*) as totale FROM preventivi GROUP BY stato", conn)
        if not df_stati.empty:
            st.bar_chart(df_stati.set_index("stato"))
        else:
            st.info("Nessun preventivo presente.")

    with col_chart2:
        st.subheader("Andamento Vendite Mensili")
        with get_connection() as conn:
            try:
                df_vendite = pd.read_sql("""
                    SELECT TO_CHAR(data_creazione, 'YYYY-MM') as mese, SUM(prezzo_totale) as totale
                    FROM preventivi WHERE stato != 'Rifiutato'
                    GROUP BY mese ORDER BY mese DESC LIMIT 6
                """, conn)
                if not df_vendite.empty:
                    st.line_chart(df_vendite.set_index("mese"))
                else:
                    st.info("Dati vendite insufficienti.")
            except Exception:
                st.info("Dati storico vendite non ancora disponibili.")

# ---------------------------------------------------------
# 2. AZIENDE
# ---------------------------------------------------------
with tab_aziende:
    st.header("🏢 Anagrafica Aziende")
    st_a1, st_a2 = st.tabs(["Aggiungi / Cerca Azienda", "Gestione ed Eliminazione"])
    
    with st_a1:
        with st.form("form_azienda", clear_on_submit=True):
            st.subheader("Nuova Azienda")
            col_a1, col_a2, col_a3 = st.columns(3)
            rs = col_a1.text_input("Ragione Sociale *")
            piva = col_a2.text_input("Partita IVA")
            email = col_a3.text_input("Email")
            tel = col_a1.text_input("Telefono")
            sdi = col_a2.text_input("Codice SDI")
            referente = col_a3.text_input("Referente Aziendale")
            
            if st.form_submit_button("Salva Azienda") and rs:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO aziende (ragione_sociale, piva, email, telefono, codice_sdi, referente)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (rs, piva, email, tel, sdi, referente))
                        conn.commit()
                st.success(f"Azienda '{rs}' aggiunta!")
                st.rerun()

        st.markdown("### 🔍 Cerca Azienda")
        search_az = st.text_input("Filtra per Ragione Sociale, P.IVA o Referente", key="search_az")
        with get_connection() as conn:
            if search_az:
                search_term = f"%{search_az}%"
                df_az = pd.read_sql(
                    "SELECT * FROM aziende WHERE ragione_sociale ILIKE %s OR piva ILIKE %s OR referente ILIKE %s",
                    conn, params=(search_term, search_term, search_term)
                )
            else:
                df_az = pd.read_sql("SELECT * FROM aziende", conn)
        st.dataframe(df_az, use_container_width=True)

    with st_a2:
        st.subheader("Modifica o Elimina Azienda")
        with get_connection() as conn:
            aziende_list = pd.read_sql("SELECT id, ragione_sociale FROM aziende ORDER BY ragione_sociale", conn)
        
        if not aziende_list.empty:
            az_selected = st.selectbox("Seleziona Azienda", aziende_list["ragione_sociale"].tolist())
            az_id = aziende_list[aziende_list["ragione_sociale"] == az_selected]["id"].values[0]
            
            with get_connection() as conn:
                az_curr = pd.read_sql("SELECT * FROM aziende WHERE id = %s", conn, params=(int(az_id),)).iloc[0]

            with st.form("edit_azienda_form"):
                e_rs = st.text_input("Ragione Sociale", value=az_curr["ragione_sociale"])
                e_piva = st.text_input("P.IVA", value=az_curr["piva"] or "")
                e_email = st.text_input("Email", value=az_curr["email"] or "")
                e_tel = st.text_input("Telefono", value=az_curr["telefono"] or "")
                e_sdi = st.text_input("Codice SDI", value=az_curr["codice_sdi"] or "")
                e_ref = st.text_input("Referente", value=az_curr["referente"] or "")
                
                c_btn1, c_btn2 = st.columns(2)
                if c_btn1.form_submit_button("💾 Salva Modifiche"):
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                UPDATE aziende SET ragione_sociale=%s, piva=%s, email=%s, telefono=%s, codice_sdi=%s, referente=%s
                                WHERE id=%s
                            """, (e_rs, e_piva, e_email, e_tel, e_sdi, e_ref, int(az_id)))
                            conn.commit()
                    st.success("Azienda aggiornata!")
                    st.rerun()

                if c_btn2.form_submit_button("🗑️ Elimina Azienda"):
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("DELETE FROM aziende WHERE id=%s", (int(az_id),))
                            conn.commit()
                    st.warning("Azienda eliminata!")
                    st.rerun()

# ---------------------------------------------------------
# 3. SETTORI E OPERATORI
# ---------------------------------------------------------
with tab_settori_op:
    st.header("⚙️ Gestione Settori e Operatori")
    col_set, col_op = st.columns(2)
    
    with col_set:
        st.subheader("📁 Settori di Produzione")
        with st.form("add_settore_form", clear_on_submit=True):
            nome_settore = st.text_input("Nome Settore")
            if st.form_submit_button("Aggiungi Settore") and nome_settore:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("INSERT INTO settori (nome) VALUES (%s)", (nome_settore,))
                        conn.commit()
                st.success("Settore creato!")
                st.rerun()

        with get_connection() as conn:
            df_settori = pd.read_sql("SELECT * FROM settori ORDER BY nome", conn)
        st.dataframe(df_settori, use_container_width=True)

        if not df_settori.empty:
            del_set = st.selectbox("Elimina Settore", df_settori["nome"].tolist(), key="del_set_sel")
            if st.button("Elimina Settore Selezionato"):
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM settori WHERE nome = %s", (del_set,))
                        conn.commit()
                st.warning("Settore eliminato!")
                st.rerun()

    with col_op:
        st.subheader("👷 Operatori")
        with get_connection() as conn:
            settori_opts = pd.read_sql("SELECT id, nome FROM settori", conn)

        with st.form("add_op_form", clear_on_submit=True):
            nome_op = st.text_input("Nome Operatore")
            settore_id_op = st.selectbox("Abbina a Settore", settori_opts["nome"].tolist() if not settori_opts.empty else [])
            
            if st.form_submit_button("Aggiungi Operatore") and nome_op and settore_id_op:
                s_id = settori_opts[settori_opts["nome"] == settore_id_op]["id"].values[0]
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("INSERT INTO operatori (nome, settore_id) VALUES (%s, %s)", (nome_op, int(s_id)))
                        conn.commit()
                st.success("Operatore inserito!")
                st.rerun()

        with get_connection() as conn:
            df_op = pd.read_sql("""
                SELECT o.id, o.nome as operatore, s.nome as settore 
                FROM operatori o LEFT JOIN settori s ON o.settore_id = s.id
            """, conn)
        st.dataframe(df_op, use_container_width=True)

# ---------------------------------------------------------
# 4. PRODOTTI
# ---------------------------------------------------------
with tab_prodotti:
    st.header("📦 Gestione Prodotti")
    p_tab1, p_tab2 = st.tabs(["Aggiungi Prodotto", "Ricerca e Modifica"])
    
    with p_tab1:
        with st.form("form_nuovo_prodotto", clear_on_submit=True):
            st.subheader("Specifiche Prodotto")
            col_p1, col_p2 = st.columns(2)
            p_nome = col_p1.text_input("Nome Prodotto *")
            p_formato = col_p2.text_input("Macchina / Gruppo / Formato")
            p_disegno = col_p1.text_input("Disegno / Codice Schema")
            p_mat = col_p2.text_input("Materiale / Trattamento")

            st.markdown("#### Ore di Lavorazione per Settore")
            with get_connection() as conn:
                settori_db = pd.read_sql("SELECT * FROM settori", conn)
            
            ore_settori = {}
            if not settori_db.empty:
                cols_s = st.columns(min(len(settori_db), 4))
                for i, row in settori_db.iterrows():
                    with cols_s[i % 4]:
                        ore_settori[row['id']] = st.number_input(f"Ore: {row['nome']}", min_value=0.0, step=0.5, value=0.0)

            col_c1, col_c2 = st.columns(2)
            costo_int = col_c1.number_input("Costo Interno (€)", min_value=0.0, step=1.0)
            prezzo_ven = col_c2.number_input("Prezzo di Vendita (€)", min_value=0.0, step=1.0)

            if st.form_submit_button("Salva Prodotto") and p_nome:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO prodotti (nome, macchina_gruppo_formato, disegno, materiale_trattamento, costo_interno, prezzo_vendita)
                            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                        """, (p_nome, p_formato, p_disegno, p_mat, costo_int, prezzo_ven))
                        new_prod_id = cur.fetchone()[0]

                        for s_id, ore_v in ore_settori.items():
                            if ore_v > 0:
                                cur.execute("""
                                    INSERT INTO prodotto_ore_settori (prodotto_id, settore_id, ore)
                                    VALUES (%s, %s, %s)
                                """, (new_prod_id, s_id, ore_v))
                        conn.commit()
                st.success(f"Prodotto '{p_nome}' salvato con successo!")
                st.rerun()

    with p_tab2:
        st.subheader("🔍 Cerca e Gestisci Prodotti")
        s_prod = st.text_input("Filtra per ID, Nome, Formato o Disegno", key="s_prod")
        
        with get_connection() as conn:
            if s_prod:
                search_p_term = f"%{s_prod}%"
                df_p = pd.read_sql(
                    "SELECT id, nome, macchina_gruppo_formato, disegno, materiale_trattamento, costo_interno, prezzo_vendita FROM prodotti WHERE nome ILIKE %s OR macchina_gruppo_formato ILIKE %s OR disegno ILIKE %s",
                    conn, params=(search_p_term, search_p_term, search_p_term)
                )
            else:
                df_p = pd.read_sql("SELECT id, nome, macchina_gruppo_formato, disegno, materiale_trattamento, costo_interno, prezzo_vendita FROM prodotti", conn)
            
            df_p["margine_%"] = df_p.apply(lambda r: round(((r["prezzo_vendita"] - r["costo_interno"]) / r["prezzo_vendita"] * 100), 2) if r["prezzo_vendita"] > 0 else 0.0, axis=1)

        st.dataframe(df_p, use_container_width=True)

        if not df_p.empty:
            del_p_id = st.selectbox("Seleziona Prodotto da Eliminare", df_p["id"].tolist())
            if st.button("🗑️ Elimina Prodotto"):
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM prodotti WHERE id = %s", (int(del_p_id),))
                        conn.commit()
                st.warning("Prodotto eliminato!")
                st.rerun()

# ---------------------------------------------------------
# 5. PREVENTIVI
# ---------------------------------------------------------
with tab_prev:
    st.header("📄 Gestione Preventivi")
    pr_tab1, pr_tab2 = st.tabs(["Crea Preventivo", "Lista e Generazione PDF"])
    
    with pr_tab1:
        with get_connection() as conn:
            az_options = pd.read_sql("SELECT id, ragione_sociale FROM aziende", conn)
            prod_options = pd.read_sql("SELECT id, nome, prezzo_vendita FROM prodotti", conn)

        if az_options.empty or prod_options.empty:
            st.warning("Inserisci almeno un'Azienda e un Prodotto prima di creare un preventivo.")
        else:
            selected_az = st.selectbox("Seleziona Cliente", az_options["ragione_sociale"].tolist())
            az_id_val = az_options[az_options["ragione_sociale"] == selected_az]["id"].values[0]

            if "cart_preventivo" not in st.session_state:
                st.session_state.cart_preventivo = []

            c_p1, c_p2, c_p3 = st.columns([3, 1, 1])
            p_sel = c_p1.selectbox("Prodotto", prod_options["nome"].tolist())
            q_sel = c_p2.number_input("Quantità", min_value=1, value=1)
            p_data = prod_options[prod_options["nome"] == p_sel].iloc[0]
            
            if c_p3.button("➕ Aggiungi"):
                st.session_state.cart_preventivo.append({
                    "prodotto_id": int(p_data["id"]),
                    "prodotto": p_sel,
                    "quantita": int(q_sel),
                    "prezzo_unitario": float(p_data["prezzo_vendita"]),
                    "prezzo_totale": float(p_data["prezzo_vendita"]) * q_sel
                })

            if st.session_state.cart_preventivo:
                df_cart = pd.DataFrame(st.session_state.cart_preventivo)
                st.table(df_cart[["prodotto", "quantita", "prezzo_unitario", "prezzo_totale"]])
                totale_prev = df_cart["prezzo_totale"].sum()
                st.markdown(f"### Totale Preventivo: `{totale_prev:,.2f} €`")

                c_sav, c_clr = st.columns(2)
                if c_sav.button("💾 Salva Preventivo"):
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                INSERT INTO preventivi (azienda_id, prezzo_totale, stato, data_creazione)
                                VALUES (%s, %s, 'In attesa', CURRENT_TIMESTAMP) RETURNING id
                            """, (int(az_id_val), totale_prev))
                            new_prev_id = cur.fetchone()[0]

                            for item in st.session_state.cart_preventivo:
                                cur.execute("""
                                    INSERT INTO preventivo_dettagli (preventivo_id, prodotto_id, quantita, prezzo_unitario, prezzo_totale)
                                    VALUES (%s, %s, %s, %s, %s)
                                """, (new_prev_id, item["prodotto_id"], item["quantita"], item["prezzo_unitario"], item["prezzo_totale"]))
                            conn.commit()
                    st.success("Preventivo salvato!")
                    st.session_state.cart_preventivo = []
                    st.rerun()

                if c_clr.button("Svuota carrello"):
                    st.session_state.cart_preventivo = []
                    st.rerun()

    with pr_tab2:
        st.subheader("Elenco e Cambi di Stato")
        with get_connection() as conn:
            df_prev_all = pd.read_sql("""
                SELECT p.id, a.ragione_sociale, p.prezzo_totale, p.stato, p.data_creazione
                FROM preventivi p LEFT JOIN aziende a ON p.azienda_id = a.id
                ORDER BY p.id DESC
            """, conn)
        st.dataframe(df_prev_all, use_container_width=True)

        if not df_prev_all.empty:
            c_action1, c_action2 = st.columns(2)
            p_action_id = c_action1.selectbox("Seleziona ID Preventivo", df_prev_all["id"].tolist())
            nuovo_stato = c_action2.selectbox("Aggiorna Stato", ["In attesa", "In lavorazione", "Completato", "Rifiutato"])

            if st.button("Aggiorna Stato Preventivo"):
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("UPDATE preventivi SET stato = %s WHERE id = %s", (nuovo_stato, int(p_action_id)))
                        conn.commit()
                st.success(f"Preventivo #{p_action_id} aggiornato!")
                st.rerun()

            with get_connection() as conn:
                prev_info = pd.read_sql("""
                    SELECT p.id, a.ragione_sociale, p.data_creazione, p.prezzo_totale
                    FROM preventivi p LEFT JOIN aziende a ON p.azienda_id = a.id WHERE p.id = %s
                """, conn, params=(int(p_action_id),)).iloc[0]

                items_info = pd.read_sql("""
                    SELECT pr.nome as prodotto, d.quantita, d.prezzo_unitario, d.prezzo_totale
                    FROM preventivo_dettagli d LEFT JOIN prodotti pr ON d.prodotto_id = pr.id WHERE d.preventivo_id = %s
                """, conn, params=(int(p_action_id),)).to_dict('records')

            data_str = str(prev_info["data_creazione"])[:10] if prev_info["data_creazione"] else datetime.today().strftime('%Y-%m-%d')
            pdf_bytes = genera_pdf_preventivo(
                prev_info["id"], prev_info["ragione_sociale"], 
                data_str, items_info, float(prev_info["prezzo_totale"])
            )

            st.download_button(
                label=f"📄 Scarica PDF Preventivo #{p_action_id}",
                data=pdf_bytes,
                file_name=f"Preventivo_{p_action_id}.pdf",
                mime="application/pdf"
            )

# ---------------------------------------------------------
# 6. LAVORAZIONE
# ---------------------------------------------------------
with tab_lav:
    st.header("🛠️ Ordini in Lavorazione")
    with get_connection() as conn:
        df_in_lav = pd.read_sql("""
            SELECT p.id, a.ragione_sociale, p.prezzo_totale, p.data_creazione
            FROM preventivi p LEFT JOIN aziende a ON p.azienda_id = a.id
            WHERE p.stato = 'In lavorazione'
        """, conn)

    if df_in_lav.empty:
        st.info("Nessun ordine in lavorazione.")
    else:
        sel_lav_id = st.selectbox("Seleziona Ordine", df_in_lav["id"].tolist())
        
        with get_connection() as conn:
            op_list = pd.read_sql("SELECT id, nome FROM operatori", conn)
            sec_list = pd.read_sql("SELECT id, nome FROM settori", conn)

        with st.form("form_registra_ore"):
            col_l1, col_l2, col_l3 = st.columns(3)
            sec_id = col_l1.selectbox("Settore", sec_list["nome"].tolist() if not sec_list.empty else [])
            op_id = col_l2.selectbox("Operatore", op_list["nome"].tolist() if not op_list.empty else [])
            ore_eff = col_l3.number_input("Ore Effettive Impiegate", min_value=0.5, step=0.5)
            note_lav = st.text_input("Note")
            
            if st.form_submit_button("💾 Registra Ore") and not sec_list.empty and not op_list.empty:
                sec_val = sec_list[sec_list["nome"] == sec_id]["id"].values[0]
                op_val = op_list[op_list["nome"] == op_id]["id"].values[0]
                
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO lavorazioni (preventivo_id, settore_id, operatore_id, ore_effettive, note)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (int(sel_lav_id), int(sec_val), int(op_val), ore_eff, note_lav))
                        conn.commit()
                st.success("Ore registrate!")
                st.rerun()

        with get_connection() as conn:
            df_hist = pd.read_sql("""
                SELECT l.id, s.nome as settore, o.nome as operatore, l.ore_effettive, l.note, l.data_registrazione
                FROM lavorazioni l
                LEFT JOIN settori s ON l.settore_id = s.id
                LEFT JOIN operatori o ON l.operatore_id = o.id
                WHERE l.preventivo_id = %s
            """, conn, params=(int(sel_lav_id),))
        st.dataframe(df_hist, use_container_width=True)

        if st.button("✅ Segna Ordine come Completato"):
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE preventivi SET stato = 'Completato' WHERE id = %s", (int(sel_lav_id),))
                    conn.commit()
            st.success(f"Ordine #{sel_lav_id} completato!")
            st.rerun()

# ---------------------------------------------------------
# 7. REPORT
# ---------------------------------------------------------
with tab_rep:
    st.header("📈 Reportistica e Analytics")
    col_r1, col_r2 = st.columns(2)
    d_inizio = col_r1.date_input("Data Inizio", value=datetime(2025, 1, 1))
    d_fine = col_r2.date_input("Data Fine", value=datetime.today())

    with get_connection() as conn:
        try:
            query_rep = """
                SELECT p.id, a.ragione_sociale, p.prezzo_totale, p.stato, p.data_creazione
                FROM preventivi p LEFT JOIN aziende a ON p.azienda_id = a.id
                WHERE p.data_creazione BETWEEN %s AND %s
            """
            df_rep = pd.read_sql(query_rep, conn, params=(d_inizio, d_fine))
        except Exception:
            df_rep = pd.DataFrame(columns=["id", "ragione_sociale", "prezzo_totale", "stato", "data_creazione"])

    st.subheader("Riepilogo Periodo Selezionato")
    r_c1, r_c2, r_c3 = st.columns(3)
    r_c1.metric("Preventivi Generati", len(df_rep))
    r_c2.metric("Valore Totale", f"{df_rep['prezzo_totale'].sum():,.2f} €" if not df_rep.empty else "0.00 €")
    r_c3.metric("Tasso di Conversione Approvati", f"{(len(df_rep[df_rep['stato'].isin(['In lavorazione', 'Completato'])]) / len(df_rep) * 100 if len(df_rep)>0 else 0):.1f}%")
    st.dataframe(df_rep, use_container_width=True)

# ---------------------------------------------------------
# 8. ASSISTENTE AI
# ---------------------------------------------------------
with tab_ai:
    st.header("🤖 Assistente AI aziendale")
    st.caption("Interroga il tuo gestionale con domande in linguaggio naturale.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Chiedi qualcosa (es. 'Qual è il cliente che ha speso di più?'):"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if client:
            try:
                with get_connection() as conn:
                    top_clients = pd.read_sql("""
                        SELECT a.ragione_sociale, SUM(p.prezzo_totale) as totale
                        FROM preventivi p JOIN aziende a ON p.azienda_id = a.id
                        WHERE p.stato IN ('In lavorazione', 'Completato')
                        GROUP BY a.ragione_sociale ORDER BY totale DESC LIMIT 5
                    """, conn).to_string()
                    
                    top_prod = pd.read_sql("SELECT nome, prezzo_vendita FROM prodotti LIMIT 5", conn).to_string()

                system_prompt = f"""
                Sei l'assistente ERP dell'azienda. Rispondi in italiano con precisione.
                Contesto attuale del DB:
                TOP CLIENTE:
                {top_clients}
                PRODOTTI PRINCIPALI:
                {top_prod}
                """

                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(system_instruction=system_prompt)
                )
                with st.chat_message("assistant"):
                    st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Errore generazione: {e}")
