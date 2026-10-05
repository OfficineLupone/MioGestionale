import os
import psycopg2
import streamlit as st
from contextlib import contextmanager


def _get_clean_db_url() -> str:
    db_url = ""

    try:
        db_url = st.secrets["DATABASE_URL"]
    except Exception:
        db_url = ""

    if not db_url:
        db_url = os.environ.get("DATABASE_URL", "")

    if not db_url:
        raise ValueError(
            "DATABASE_URL non trovato. Aggiungilo nei Secrets di Streamlit "
            "oppure nelle variabili d'ambiente."
        )

    db_url = db_url.strip().strip('"').strip("'")

    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    if "channel_binding=" in db_url:
        db_url = db_url.replace("&channel_binding=require", "")
        db_url = db_url.replace("?channel_binding=require", "")

    if "sslmode=" not in db_url:
        separator = "&" if "?" in db_url else "?"
        db_url = f"{db_url}{separator}sslmode=require"

    return db_url


@contextmanager
def get_connection():
    """Apre una connessione PostgreSQL/Neon con timeout di sicurezza."""
    db_url = _get_clean_db_url()
    conn = None

    try:
        conn = psycopg2.connect(db_url, connect_timeout=10)
        yield conn

    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        raise RuntimeError(f"Errore connessione database: {e}") from e

    finally:
        if conn:
            conn.close()


def get_db_uri() -> str:
    return _get_clean_db_url()


def init_db():
    """Crea le tabelle necessarie e propaga eventuali errori."""
    try:
        with get_connection() as conn:
            with conn.cursor() as c:
                c.execute("""
                    CREATE TABLE IF NOT EXISTS settori (
                        id SERIAL PRIMARY KEY,
                        nome VARCHAR(255) UNIQUE NOT NULL
                    )
                """)

                c.execute("""
                    CREATE TABLE IF NOT EXISTS operatori (
                        id SERIAL PRIMARY KEY,
                        nome VARCHAR(255) NOT NULL,
                        settore_id INTEGER NOT NULL REFERENCES settori(id) ON DELETE CASCADE
                    )
                """)

                c.execute("""
                    CREATE TABLE IF NOT EXISTS prodotti (
                        id SERIAL PRIMARY KEY,
                        nome VARCHAR(255) UNIQUE NOT NULL,
                        materiale_trattamento TEXT,
                        macchina_gruppo_formato TEXT,
                        disegno TEXT,
                        costo_interno REAL NOT NULL DEFAULT 0.0,
                        prezzo_vendita REAL NOT NULL DEFAULT 0.0
                    )
                """)

                colonne_prodotti = [
                    ("materiale_trattamento", "TEXT"),
                    ("macchina_gruppo_formato", "TEXT"),
                    ("disegno", "TEXT"),
                    ("costo_interno", "REAL NOT NULL DEFAULT 0.0"),
                    ("prezzo_vendita", "REAL NOT NULL DEFAULT 0.0")
                ]

                for col_nome, col_def in colonne_prodotti:
                    c.execute(
                        f"ALTER TABLE prodotti ADD COLUMN IF NOT EXISTS {col_nome} {col_def};"
                    )

                c.execute("""
                    CREATE TABLE IF NOT EXISTS prodotto_ore_settori (
                        prodotto_id INTEGER REFERENCES prodotti(id) ON DELETE CASCADE,
                        settore_id INTEGER REFERENCES settori(id) ON DELETE CASCADE,
                        ore REAL NOT NULL DEFAULT 0.0,
                        PRIMARY KEY (prodotto_id, settore_id)
                    )
                """)

                c.execute("""
                    CREATE TABLE IF NOT EXISTS aziende (
                        id SERIAL PRIMARY KEY,
                        ragione_sociale VARCHAR(255) UNIQUE NOT NULL,
                        piva VARCHAR(50),
                        email VARCHAR(255)
                    )
                """)

                c.execute("""
                    CREATE TABLE IF NOT EXISTS preventivi (
                        id SERIAL PRIMARY KEY,
                        azienda_id INTEGER REFERENCES aziende(id) ON DELETE SET NULL,
                        prodotto_id INTEGER REFERENCES prodotti(id) ON DELETE SET NULL,
                        quantita INTEGER,
                        prezzo_totale REAL,
                        ore_totali_stimate REAL,
                        stato VARCHAR(50) DEFAULT 'In attesa'
                    )
                """)

                c.execute("""
                    CREATE TABLE IF NOT EXISTS lavori (
                        id SERIAL PRIMARY KEY,
                        preventivo_id INTEGER REFERENCES preventivi(id) ON DELETE CASCADE,
                        settore_nome VARCHAR(255),
                        ore_effettive REAL,
                        note TEXT
                    )
                """)

            conn.commit()

    except Exception as e:
        raise RuntimeError(f"Errore durante l'inizializzazione del database: {e}") from e
