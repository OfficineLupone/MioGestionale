import os
import psycopg2
from contextlib import contextmanager

def _get_clean_db_url() -> str:
    db_url = ""
    
    # 1. Prova prima a recuperare dai secrets di Streamlit se disponibile
    try:
        import streamlit as st
        db_url = st.secrets.get("DATABASE_URL", "")
    except Exception:
        pass
        
    # 2. Se non presente in st.secrets, recupera dalle variabili d'ambiente
    if not db_url:
        db_url = os.environ.get("DATABASE_URL", "")

    if not db_url:
        raise ValueError("DATABASE_URL non trovato nei Secrets di Streamlit o nelle variabili di ambiente!")

    # Corregge 'postgres://' in 'postgresql://' per compatibilità con SQLAlchemy/psycopg2
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    # Rimuove channel_binding se presente (può causare problemi con alcune versioni di libpq)
    if "channel_binding=" in db_url:
        db_url = db_url.replace("&channel_binding=require", "").replace("?channel_binding=require", "")

    # Assicura sslmode=require per connessioni sicure con Neon Cloud DB
    if "sslmode=" not in db_url:
        separator = "&" if "?" in db_url else "?"
        db_url = f"{db_url}{separator}sslmode=require"

    return db_url

def get_raw_connection():
    """Apre e restituisce una singola connessione a PostgreSQL."""
    db_url = _get_clean_db_url()
    return psycopg2.connect(db_url, connect_timeout=5)

@contextmanager
def get_connection():
    """Context Manager per gestire automaticamente apertura, commit/rollback e chiusura della connessione."""
    conn = get_raw_connection()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_db_uri() -> str:
    """Restituisce l'URL del database pulito."""
    return _get_clean_db_url()

def init_db():
    """Inizializza la struttura delle tabelle nel database Neon se non esistono."""
    with get_connection() as conn:
        with conn.cursor() as c:
            # 1. Settori
            c.execute('''CREATE TABLE IF NOT EXISTS settori (
                id SERIAL PRIMARY KEY, 
                nome VARCHAR(255) UNIQUE NOT NULL)''')

            # 2. Operatori
            c.execute('''CREATE TABLE IF NOT EXISTS operatori (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(255) NOT NULL,
                settore_id INTEGER NOT NULL REFERENCES settori(id) ON DELETE CASCADE)''')

            # 3. Prodotti
            c.execute('''CREATE TABLE IF NOT EXISTS prodotti (
                id SERIAL PRIMARY KEY, 
                nome VARCHAR(255) UNIQUE NOT NULL, 
                materiale_trattamento TEXT,
                macchina_gruppo_formato TEXT,
                disegno TEXT,
                costo_interno REAL NOT NULL DEFAULT 0.0, 
                prezzo_vendita REAL NOT NULL DEFAULT 0.0)''')

            # Migrazione automatica colonne nel caso la tabella esistesse già con schema vecchio
            colonne_prodotti = [
                ("materiale_trattamento", "TEXT"),
                ("macchina_gruppo_formato", "TEXT"),
                ("disegno", "TEXT"),
                ("costo_interno", "REAL NOT NULL DEFAULT 0.0"),
                ("prezzo_vendita", "REAL NOT NULL DEFAULT 0.0")
            ]

            for col_nome, col_def in colonne_prodotti:
                c.execute(f"ALTER TABLE prodotti ADD COLUMN IF NOT EXISTS {col_nome} {col_def};")

            # 4. Ore per Settore
            c.execute('''CREATE TABLE IF NOT EXISTS prodotto_ore_settori (
                prodotto_id INTEGER REFERENCES prodotti(id) ON DELETE CASCADE,
                settore_id INTEGER REFERENCES settori(id) ON DELETE CASCADE,
                ore REAL NOT NULL DEFAULT 0.0,
                PRIMARY KEY (prodotto_id, settore_id))''')

            # 5. Aziende
            c.execute('''CREATE TABLE IF NOT EXISTS aziende (
                id SERIAL PRIMARY KEY, 
                ragione_sociale VARCHAR(255) UNIQUE NOT NULL, 
                piva VARCHAR(50), 
                email VARCHAR(255))''')

            # 6. Preventivi
            c.execute('''CREATE TABLE IF NOT EXISTS preventivi (
                id SERIAL PRIMARY KEY, 
                azienda_id INTEGER REFERENCES aziende(id) ON DELETE SET NULL, 
                prodotto_id INTEGER REFERENCES prodotti(id) ON DELETE SET NULL, 
                quantita INTEGER, 
                prezzo_totale REAL, 
                ore_totali_stimate REAL, 
                stato VARCHAR(50) DEFAULT 'In attesa')''')

            # 7. Lavori
            c.execute('''CREATE TABLE IF NOT EXISTS lavori (
                id SERIAL PRIMARY KEY, 
                preventivo_id INTEGER REFERENCES preventivi(id) ON DELETE CASCADE, 
                settore_nome VARCHAR(255), 
                ore_effettive REAL, 
                note TEXT)''')

        conn.commit()

if __name__ == "__main__":
    init_db()
    print("Database inizializzato con successo!")
