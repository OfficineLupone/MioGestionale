import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
from sqlalchemy import create_engine, text

import database

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="OFFICINE LUPONE - Dashboard",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)


@st.cache_resource
def inizializza_db_sicuro():
    try:
        database.init_db()
        return True, "Database inizializzato correttamente."
    except Exception as e:
        return False, str(e)


db_ok, db_message = inizializza_db_sicuro()

if not db_ok:
    st.error(f"⚠️ Impossibile inizializzare il database Neon: {db_message}")
    st.stop()

# --- 2. CSS PERSONALIZZATO ---
st.markdown("""
    <style>
    .stApp { background-color: #f6f8f7; }
    #MainMenu, footer, header { visibility: hidden; }

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

    .stButton>button[kind="primary"] {
        background-color: #0e3d2f !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
    }
    </style>
""", unsafe_allow_html=True)

try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    api_key = ""

# --- 3. FUNZIONI OPERATIVE DB ---
def aggiungi_settore_db(nome_settore: str) -> str:
    """Aggiunge un nuovo settore produttivo.

    Args:
        nome_settore: Nome del settore da aggiungere.

    Returns:
        Esito dell'operazione.
    """
    if not nome_settore or not nome_settore.strip():
        return "❌ Il nome del settore non può essere vuoto!"

    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute(
                    """
                    INSERT INTO settori (nome)
                    VALUES (%s)
                    ON CONFLICT (nome) DO NOTHING;
                    """,
                    (nome_settore.strip(),)
                )
            conn.commit()

        return f"✅ Settore '{nome_settore.strip()}' aggiunto!"

    except Exception as e:
        return f"❌ Errore durante l'inserimento: {e}"


def rinomina_settore_db(vecchio_nome: str, nuovo_nome: str) -> str:
    """Rinomina un settore produttivo esistente.

    Args:
        vecchio_nome: Nome attuale del settore.
        nuovo_nome: Nuovo nome del settore.

    Returns:
        Esito dell'operazione.
    """
    if not nuovo_nome or not nuovo_nome.strip():
        return "❌ Il nuovo nome non può essere vuoto!"

    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute(
                    "UPDATE settori SET nome = %s WHERE nome = %s",
                    (nuovo_nome.strip(), vecchio_nome)
                )
            conn.commit()

        return f"✅ Settore '{vecchio_nome}' rinominato in '{nuovo_nome.strip()}'!"

    except Exception as e:
        return f"❌ Errore: {e}"


def elimina_settore_db(nome_settore: str) -> str:
    """Elimina un settore produttivo.

    Args:
        nome_settore: Nome del settore da eliminare.

    Returns:
        Esito dell'operazione.
    """
    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute("DELETE FROM settori WHERE nome = %s", (nome_settore,))
            conn.commit()

        return f"🗑️ Settore '{nome_settore}' eliminato!"

    except Exception as e:
        return f"❌ Errore: {e}"


def aggiungi_operatore_db(nome_operatore: str, settore_id: int) -> str:
    """Aggiunge un operatore a un settore.

    Args:
        nome_operatore: Nome dell'operatore.
        settore_id: ID del settore di destinazione.

    Returns:
        Esito dell'operazione.
    """
    if not nome_operatore or not nome_operatore.strip():
        return "❌ Il nome dell'operatore non può essere vuoto!"

    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute(
                    "INSERT INTO operatori (nome, settore_id) VALUES (%s, %s)",
                    (nome_operatore.strip(), settore_id)
                )
            conn.commit()

        return f"✅ Operatore '{nome_operatore.strip()}' aggiunto!"

    except Exception as e:
        return f"❌ Errore: {e}"


def elimina_operatore_db(operatore_id: int) -> str:
    """Elimina un operatore.

    Args:
        operatore_id: ID dell'operatore da eliminare.

    Returns:
        Esito dell'operazione.
    """
    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute("DELETE FROM operatori WHERE id = %s", (operatore_id,))
            conn.commit()

        return "🗑️ Operatore rimosso!"

    except Exception as e:
        return f"❌ Errore: {e}"


def reset_settori_ai(nuovi_settori: str) -> str:
    """Sostituisce tutti i settori con una nuova lista.

    Args:
        nuovi_settori: Nomi dei settori separati da virgola.

    Returns:
        Esito dell'operazione.
    """
    settori = [s.strip() for s in nuovi_settori.split(",") if s.strip()]

    if not settori:
        return "❌ Fornisci almeno un settore valido."

    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute("TRUNCATE TABLE settori RESTART IDENTITY CASCADE")

                for settore in settori:
                    c.execute(
                        "INSERT INTO settori (nome) VALUES (%s)",
                        (settore,)
                    )

            conn.commit()

        return f"✅ Settori resettati: {', '.join(settori)}"

    except Exception as e:
        return f"❌ Errore: {e}"


def salva_prodotto_esteso(
    particolare: str,
    mat_tratt: str,
    macch_gruppo: str,
    disegno: str,
    costo: float,
    prezzo: float,
    ore_settori: dict
) -> str:
    """Salva o aggiorna un prodotto e le ore per settore.

    Args:
        particolare: Nome del prodotto.
        mat_tratt: Materiale o trattamento.
        macch_gruppo: Macchina, gruppo o formato.
        disegno: Riferimento disegno.
        costo: Costo interno.
        prezzo: Prezzo di vendita.
        ore_settori: Dizionario con ID settore e ore.

    Returns:
        Esito dell'operazione.
    """
    if not particolare or not particolare.strip():
        return "❌ Il campo 'Particolare' è obbligatorio!"

    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute(
                    """
                    INSERT INTO prodotti (
                        nome, materiale_trattamento, macchina_gruppo_formato,
                        disegno, costo_interno, prezzo_vendita
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (nome) DO UPDATE SET
                        materiale_trattamento = EXCLUDED.materiale_trattamento,
                        macchina_gruppo_formato = EXCLUDED.macchina_gruppo_formato,
                        disegno = EXCLUDED.disegno,
                        costo_interno = EXCLUDED.costo_interno,
                        prezzo_vendita = EXCLUDED.prezzo_vendita
                    RETURNING id;
                    """,
                    (
                        particolare.strip(),
                        mat_tratt.strip(),
                        macch_gruppo.strip(),
                        disegno.strip(),
                        costo,
                        prezzo
                    )
                )

                prodotto_id = c.fetchone()[0]

                for settore_id, ore in ore_settori.items():
                    if ore > 0:
                        c.execute(
                            """
                            INSERT INTO prodotto_ore_settori (prodotto_id, settore_id, ore)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (prodotto_id, settore_id)
                            DO UPDATE SET ore = EXCLUDED.ore;
                            """,
                            (prodotto_id, settore_id, ore)
                        )
                    else:
                        c.execute(
                            """
                            DELETE FROM prodotto_ore_settori
                            WHERE prodotto_id = %s AND settore_id = %s;
                            """,
                            (prodotto_id, settore_id)
                        )

            conn.commit()

        return f"✅ Prodotto '{particolare.strip()}' salvato con successo!"

    except Exception as e:
        return f"❌ Errore durante il salvataggio: {e}"


def elimina_prodotto_db(nome_prodotto: str) -> str:
    """Elimina un prodotto dal catalogo.

    Args:
        nome_prodotto: Nome del prodotto da eliminare.

    Returns:
        Esito dell'operazione.
    """
    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute("DELETE FROM prodotti WHERE nome = %s", (nome_prodotto,))
            conn.commit()

        return f"🗑️ Prodotto '{nome_prodotto}' eliminato!"

    except Exception as e:
        return f"❌ Errore: {e}"


tools_map = {
    "aggiungi_settore_db": aggiungi_settore_db,
    "rinomina_settore_db": rinomina_settore_db,
    "reset_settori_ai": reset_settori_ai
}

tools_list = [
    aggiungi_settore_db,
    rinomina_settore_db,
    reset_settori_ai
]

# --- 4. CARICAMENTO DATI ---
@st.cache_data(ttl=30)
def carica_dati():
    try:
        engine = create_engine(database.get_db_uri(), pool_pre_ping=True)

        with engine.connect() as conn:
            df_settori = pd.read_sql_query(
                text('SELECT id AS "ID", nome AS "Nome Settore" FROM settori ORDER BY id'),
                conn
            )

            df_operatori = pd.read_sql_query(
                text("""
                    SELECT
                        o.id AS "ID",
                        o.nome AS "Nome Operatore",
                        s.nome AS "Settore",
                        o.settore_id
                    FROM operatori o
                    JOIN settori s ON o.settore_id = s.id
                    ORDER BY o.id
                """),
                conn
            )

            df_prodotti = pd.read_sql_query(
                text("""
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
                    GROUP BY
                        p.id,
                        p.nome,
                        p.materiale_trattamento,
                        p.macchina_gruppo_formato,
                        p.disegno,
                        p.costo_interno,
                        p.prezzo_vendita
                    ORDER BY p.id
                """),
                conn
            )

        return df_settori, df_operatori, df_prodotti

    except Exception as err:
        st.error(f"Errore durante il caricamento dei dati: {err}")

        return (
            pd.DataFrame(columns=["ID", "Nome Settore"]),
            pd.DataFrame(columns=["ID", "Nome Operatore", "Settore", "settore_id"]),
            pd.DataFrame(
                columns=[
                    "ID", "Particolare", "Materiale / Trattamento",
                    "Macchina / Gruppo / Formato", "Disegno", "Ore Totali",
                    "Costo (€)", "Prezzo (€)"
                ]
            )
        )


df_settori, df_operatori, df_prodotti = carica_dati()

# --- 5. HEADER ---
st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
        <div style="background-color: #0e3d2f; color: white; padding: 8px 12px; border-radius: 8px; font-weight: bold;">🛡️</div>
        <div>
            <div class="brand-title">OFFICINE LUPONE - GESTIONALE ENTERPRISE</div>
            <div class="brand-sub">Sistema Integrato AI • Versione Cloud</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 6. TABS ---
tab_panoramica, tab_settori, tab_prodotti, tab_assistente = st.tabs([
    "Panoramica",
    "Settori Produttivi",
    "Catalogo Prodotti",
    "💬 Assistente IA"
])

# --- TAB PANORAMICA ---
with tab_panoramica:
    st.markdown("## Panoramica Generale")

    k1, k2, k3 = st.columns(3)
    k1.metric("Settori Registrati", len(df_settori))
    k2.metric("Operatori Totali", len(df_operatori))
    k3.metric("Prodotti a Catalogo", len(df_prodotti))

    st.write("")

    c_left, c_right = st.columns(2)

    with c_left:
        st.markdown("### 🏬 Settori")
        st.dataframe(df_settori, use_container_width=True, hide_index=True)

    with c_right:
        st.markdown("### 👷‍♂️ Operatori")

        if not df_operatori.empty:
            st.dataframe(
                df_operatori[["Nome Operatore", "Settore"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.dataframe(df_operatori, use_container_width=True, hide_index=True)

# --- TAB SETTORI ---
with tab_settori:
    st.markdown("## 🏬 Gestione Settori & Operatori")

    col_s1, col_s2, col_s3, col_s4 = st.columns(4)

    with col_s1:
        with st.popover("➕ Nuovo Settore", use_container_width=True):
            nuovo_s = st.text_input("Nome Settore:")

            if st.button("Salva Settore", type="primary"):
                if nuovo_s:
                    st.toast(aggiungi_settore_db(nuovo_s))
                    st.cache_data.clear()
                    st.rerun()

    with col_s2:
        with st.popover("✏️ Rinomina Settore", use_container_width=True):
            if not df_settori.empty:
                s_sel = st.selectbox("Seleziona:", df_settori["Nome Settore"].tolist())
                s_new = st.text_input("Nuovo nome:", value=s_sel)

                if st.button("Conferma Rinomina", type="primary"):
                    st.toast(rinomina_settore_db(s_sel, s_new))
                    st.cache_data.clear()
                    st.rerun()

    with col_s3:
        with st.popover("🗑 Elimina Settore", use_container_width=True):
            if not df_settori.empty:
                s_del = st.selectbox(
                    "Seleziona da eliminare:",
                    df_settori["Nome Settore"].tolist()
                )

                if st.button("Conferma Eliminazione"):
                    st.toast(elimina_settore_db(s_del))
                    st.cache_data.clear()
                    st.rerun()

    with col_s4:
        with st.popover("👷‍♂ Aggiungi Operatore", use_container_width=True):
            if not df_settori.empty:
                set_target = st.selectbox(
                    "Assegna al Settore:",
                    df_settori["Nome Settore"].tolist()
                )
                op_nome = st.text_input("Nome Operatore:")

                if st.button("Salva Operatore", type="primary"):
                    if op_nome:
                        s_id = df_settori[
                            df_settori["Nome Settore"] == set_target
                        ]["ID"].values[0]

                        st.toast(aggiungi_operatore_db(op_nome, int(s_id)))
                        st.cache_data.clear()
                        st.rerun()

    st.write("")
    st.dataframe(df_settori, use_container_width=True, hide_index=True)

# --- TAB CATALOGO ---
with tab_prodotti:
    st.markdown("## 📋 Catalogo Prodotti")

    with st.popover("➕ Aggiungi Prodotto Completo"):
        p_particolare = st.text_input("Particolare:")
        p_mat_tratt = st.text_input("Materiale / Trattamento:")
        p_macch_grup = st.text_input("Macchina / Gruppo:")
        p_disegno = st.text_input("Disegno:")

        ore_settori_dict = {}

        if not df_settori.empty:
            for _, s_row in df_settori.iterrows():
                val_ore = st.number_input(
                    f"Ore: {s_row['Nome Settore']}",
                    min_value=0.0,
                    step=0.5
                )
                ore_settori_dict[int(s_row["ID"])] = val_ore

        p_costo = st.number_input("Costo Interno (€):", min_value=0.0, step=10.0)
        p_prezzo = st.number_input("Prezzo Vendita (€):", min_value=0.0, step=10.0)

        if st.button("Salva Prodotto", type="primary"):
            if p_particolare:
                st.toast(
                    salva_prodotto_esteso(
                        p_particolare,
                        p_mat_tratt,
                        p_macch_grup,
                        p_disegno,
                        p_costo,
                        p_prezzo,
                        ore_settori_dict
                    )
                )
                st.cache_data.clear()
                st.rerun()

    st.write("")
    st.dataframe(df_prodotti, use_container_width=True, hide_index=True)

# --- TAB ASSISTENTE IA ---
with tab_assistente:
    st.markdown("## 💬 Assistente AI")
    st.caption("Esegui azioni sul gestionale in linguaggio naturale.")

    cmd = st.text_input(
        "Impartisci un comando all'IA:",
        placeholder="Es. Aggiungi il settore Tranciatura..."
    )

    if st.button("🚀 Esegui Comando", type="primary") and cmd:
        if not api_key:
            st.error("Configura GEMINI_API_KEY nei Secrets di Streamlit!")
        else:
            client = genai.Client(api_key=api_key)

            with st.spinner("Comunicazione con l'IA in corso..."):
                try:
                    response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=cmd,
                        config=types.GenerateContentConfig(
                            tools=tools_list,
                            temperature=0
                        )
                    )

                    executed_any = False

                    if getattr(response, "function_calls", None):
                        for fn_call in response.function_calls:
                            if fn_call.name in tools_map:
                                args = dict(fn_call.args) if fn_call.args else {}
                                res = tools_map[fn_call.name](**args)
                                st.success(res)
                                executed_any = True

                    if executed_any:
                        st.cache_data.clear()
                        st.rerun()

                    elif getattr(response, "text", None):
                        st.info(response.text)

                    else:
                        st.warning("Il modello non ha identificato comandi eseguibili.")

                except Exception as e:
                    st.error(f"Si è verificato un errore durante l'elaborazione: {e}")
