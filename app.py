import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
from sqlalchemy import create_engine, text

import database

# ------------------------------
# CONFIGURAZIONE
# ------------------------------

st.set_page_config(
    page_title="Officine Lupone",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

COLORI = {
    "primario": "#0F3D3E",
    "secondario": "#14532D",
    "accento": "#16A34A",
    "sfondo": "#F4F7F6",
    "card": "#FFFFFF",
    "testo": "#111827",
    "muted": "#6B7280",
    "bordo": "#E5E7EB"
}

st.markdown(f"""
<style>
    .stApp {{
        background-color: {COLORI['sfondo']};
        color: {COLORI['testo']};
    }}

    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #0F3D3E 0%, #14532D 100%);
        color: white;
    }}

    section[data-testid="stSidebar"] * {{
        color: #E5E7EB !important;
    }}

    section[data-testid="stSidebar"] .stRadio label {{
        background: rgba(255,255,255,0.06);
        border-radius: 10px;
        padding: 8px 12px;
        margin-bottom: 4px;
        transition: 0.2s;
    }}

    section[data-testid="stSidebar"] .stRadio label:hover {{
        background: rgba(255,255,255,0.14);
    }}

    .main-title {{
        font-size: 2rem;
        font-weight: 800;
        color: {COLORI['primario']};
        letter-spacing: -0.5px;
    }}

    .main-subtitle {{
        color: {COLORI['muted']};
        font-size: 0.95rem;
        margin-top: -8px;
    }}

    .section-title {{
        font-size: 1.25rem;
        font-weight: 700;
        color: {COLORI['primario']};
        margin-bottom: 0.5rem;
    }}

    div[data-testid="stMetric"] {{
        background: {COLORI['card']};
        border: 1px solid {COLORI['bordo']};
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 4px 14px rgba(15, 61, 62, 0.06);
    }}

    div[data-testid="stMetricLabel"] {{
        color: {COLORI['muted']};
        font-weight: 600;
    }}

    div[data-testid="stMetricValue"] {{
        color: {COLORI['primario']};
        font-weight: 800;
    }}

    .stButton > button {{
        border-radius: 10px;
        border: 1px solid {COLORI['bordo']};
        font-weight: 600;
        transition: all 0.2s ease;
    }}

    .stButton > button[kind="primary"] {{
        background: {COLORI['primario']} !important;
        color: white !important;
        border: none !important;
    }}

    .stButton > button[kind="primary"]:hover {{
        background: {COLORI['secondario']} !important;
        transform: translateY(-1px);
    }}

    .stButton > button[kind="secondary"]:hover {{
        border-color: {COLORI['primario']};
        color: {COLORI['primario']};
    }}

    div[data-testid="stDataFrame"] {{
        border: 1px solid {COLORI['bordo']};
        border-radius: 12px;
        overflow: hidden;
        background: white;
    }}

    .card {{
        background: {COLORI['card']};
        border: 1px solid {COLORI['bordo']};
        border-radius: 14px;
        padding: 20px;
        box-shadow: 0 4px 14px rgba(15, 61, 62, 0.06);
    }}

    .empty-state {{
        text-align: center;
        color: {COLORI['muted']};
        padding: 28px;
        border: 1px dashed {COLORI['bordo']};
        border-radius: 14px;
        background: white;
    }}
</style>
""", unsafe_allow_html=True)

# ------------------------------
# DATABASE
# ------------------------------

@st.cache_resource
def inizializza_db_sicuro():
    try:
        database.init_db()
        return True, "Database connesso correttamente."
    except Exception as e:
        return False, str(e)


db_ok, db_message = inizializza_db_sicuro()

if not db_ok:
    st.error(f"⚠️ Impossibile connettersi al database: {db_message}")
    st.stop()

try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    api_key = ""

# ------------------------------
# FUNZIONI DATABASE
# ------------------------------

def aggiungi_settore_db(nome_settore: str) -> str:
    """Aggiunge un settore produttivo.

    Args:
        nome_settore: Nome del settore.

    Returns:
        Esito dell'operazione.
    """
    if not nome_settore.strip():
        return "❌ Inserisci il nome del settore."

    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute(
                    "INSERT INTO settori (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING;",
                    (nome_settore.strip(),)
                )
            conn.commit()
        return f"✅ Settore “{nome_settore.strip()}” aggiunto."
    except Exception as e:
        return f"❌ Errore: {e}"


def rinomina_settore_db(vecchio_nome: str, nuovo_nome: str) -> str:
    """Rinomina un settore produttivo.

    Args:
        vecchio_nome: Nome attuale.
        nuovo_nome: Nuovo nome.

    Returns:
        Esito dell'operazione.
    """
    if not nuovo_nome.strip():
        return "❌ Inserisci il nuovo nome."

    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute(
                    "UPDATE settori SET nome = %s WHERE nome = %s;",
                    (nuovo_nome.strip(), vecchio_nome)
                )
            conn.commit()
        return f"✅ Settore rinominato in “{nuovo_nome.strip()}”."
    except Exception as e:
        return f"❌ Errore: {e}"


def elimina_settore_db(nome_settore: str) -> str:
    """Elimina un settore produttivo.

    Args:
        nome_settore: Nome del settore.

    Returns:
        Esito dell'operazione.
    """
    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute("DELETE FROM settori WHERE nome = %s;", (nome_settore,))
            conn.commit()
        return f"🗑️ Settore “{nome_settore}” eliminato."
    except Exception as e:
        return f"❌ Errore: {e}"


def aggiungi_operatore_db(nome_operatore: str, settore_id: int) -> str:
    """Aggiunge un operatore a un settore.

    Args:
        nome_operatore: Nome dell'operatore.
        settore_id: ID settore.

    Returns:
        Esito dell'operazione.
    """
    if not nome_operatore.strip():
        return "❌ Inserisci il nome dell’operatore."

    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute(
                    "INSERT INTO operatori (nome, settore_id) VALUES (%s, %s);",
                    (nome_operatore.strip(), settore_id)
                )
            conn.commit()
        return f"✅ Operatore “{nome_operatore.strip()}” aggiunto."
    except Exception as e:
        return f"❌ Errore: {e}"


def elimina_operatore_db(operatore_id: int) -> str:
    """Elimina un operatore.

    Args:
        operatore_id: ID operatore.

    Returns:
        Esito dell'operazione.
    """
    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute("DELETE FROM operatori WHERE id = %s;", (operatore_id,))
            conn.commit()
        return "🗑️ Operatore eliminato."
    except Exception as e:
        return f"❌ Errore: {e}"


def reset_settori_ai(nuovi_settori: str) -> str:
    """Sostituisce tutti i settori.

    Args:
        nuovi_settori: Nomi separati da virgola.

    Returns:
        Esito dell'operazione.
    """
    settori = [s.strip() for s in nuovi_settori.split(",") if s.strip()]

    if not settori:
        return "❌ Fornisci almeno un settore."

    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute("TRUNCATE TABLE settori RESTART IDENTITY CASCADE;")
                for settore in settori:
                    c.execute("INSERT INTO settori (nome) VALUES (%s);", (settore,))
            conn.commit()
        return f"✅ Settori aggiornati: {', '.join(settori)}."
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
    """Salva o aggiorna un prodotto.

    Args:
        particolare: Nome prodotto.
        mat_tratt: Materiale o trattamento.
        macch_gruppo: Macchina, gruppo o formato.
        disegno: Disegno.
        costo: Costo interno.
        prezzo: Prezzo di vendita.
        ore_settori: Ore per settore.

    Returns:
        Esito dell'operazione.
    """
    if not particolare.strip():
        return "❌ Il campo Particolare è obbligatorio."

    try:
        with database.get_connection() as conn:
            with conn.cursor() as c:
                c.execute("""
                    INSERT INTO prodotti (
                        nome, materiale_trattamento, macchina_gruppo_formato,
                        disegno, costo_interno, prezzo_vendita
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (nome) DO UPDATE SET
                        materiale_trattamento = EXCLUDED.materiale_trattamento,
                        macchina_gruppo_formato = EXCLUDED.macchina_gruppo_formato,
                        disegno = EXCLUDED.disegno,
