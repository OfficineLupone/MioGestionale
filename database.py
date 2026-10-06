import os
import psycopg2
import streamlit as st
from contextlib import contextmanager

def _get_clean_db_url() -> str:
    db_url = st.secrets.get("DATABASE_URL", "") or os.environ.get("DATABASE_URL", "")
    
    if not db_url:
        raise ValueError(
            "DATABASE_URL non trovato nei Secrets di Streamlit o nelle variabili d'ambiente."
        )

    db_url = db_url.strip().strip('"').strip("'")

    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    if "channel_binding=" in db_url:
        db_url = db_url.replace("&channel_binding=require", "").replace("?channel_binding=require", "")

    if "sslmode=" not in db_url:
        separator = "&" if "?" in db_url else "?"
        db_url = f"{db_url}{separator}sslmode=require"

    return db_url

@contextmanager
def get_connection():
    """Apre una connessione PostgreSQL con gestione sicura dei rollback e delle chiusure."""
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

def init_db():
    """Inizializza lo schema del database con vincoli e indici ottimali."""
    try:
        with get_connection() as conn:
            with conn.cursor() as c:
                # Tabella Settori
                c.execute("""
                    CREATE TABLE IF NOT EXISTS settori (
                        id SERIAL PRIMARY KEY,
                        nome VARCHAR(255) UNIQUE NOT NULL
                    );
                """)

                # Tabella Operatori
                c.execute("""
                    CREATE TABLE IF NOT EXISTS operatori (
                        id SERIAL PRIMARY KEY,
                        nome VARCHAR(255) NOT NULL,
                        settore_id INTEGER NOT NULL REFERENCES settori(id) ON DELETE CASCADE
                    );
                """)

                # Tabella Prodotti
                c.execute("""
                    CREATE TABLE IF NOT EXISTS prodotti (
                        id SERIAL PRIMARY KEY,
                        nome VARCHAR(255) UNIQUE NOT NULL,
                        materiale_trattamento TEXT,
                        macchina_gruppo_formato TEXT,
                        disegno TEXT,
                        costo_interno NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                        prezzo_vendita NUMERIC(10, 2) NOT NULL DEFAULT 0.00
                    );
                """)

                # Tabella Relazione Prodotto-Ore-Settori
                c.execute("""
                    CREATE TABLE IF NOT EXISTS prodotto_ore_settori (
                        prodotto_id INTEGER REFERENCES prodotti(id) ON DELETE CASCADE,
                        settore_id INTEGER REFERENCES settori(id) ON DELETE CASCADE,
                        ore NUMERIC(8, 2) NOT NULL DEFAULT 0.00,
                        PRIMARY KEY (prodotto_id, settore_id)
                    );
                """)

                # Tabella Aziende
                c.execute("""
                    CREATE TABLE IF NOT EXISTS aziende (
                        id SERIAL PRIMARY KEY,
                        ragione_sociale VARCHAR(255) UNIQUE NOT NULL,
                        piva VARCHAR(50),
                        email VARCHAR(255)
                    );
                """)

                # Tabella Preventivi
                c.execute("""
                    CREATE TABLE IF NOT EXISTS preventivi (
                        id SERIAL PRIMARY KEY,
                        azienda_id INTEGER REFERENCES aziende(id) ON DELETE SET NULL,
                        prodotto_id INTEGER REFERENCES prodotti(id) ON DELETE SET NULL,
                        quantita INTEGER NOT NULL DEFAULT 1,
                        prezzo_totale NUMERIC(10, 2) DEFAULT 0.00,
                        ore_totali_stimate NUMERIC(8, 2) DEFAULT 0.00,
                        stato VARCHAR(50) DEFAULT 'In attesa'
                    );
                """)

                # Tabella Lavori/Consuntivo
                c.execute("""
                    CREATE TABLE IF NOT EXISTS lavori (
                        id SERIAL PRIMARY KEY,
                        preventivo_id INTEGER REFERENCES preventivi(id) ON DELETE CASCADE,
                        settore_nome VARCHAR(255),
                        ore_effettive NUMERIC(8, 2) DEFAULT 0.00,
                        note TEXT
                    );
                """)

                # Indici per velocizzare le JOIN frequenti
                c.execute("CREATE INDEX IF NOT EXISTS idx_preventivi_azienda ON preventivi(azienda_id);")
                c.execute("CREATE INDEX IF NOT EXISTS idx_preventivi_prodotto ON preventivi(prodotto_id);")
                
            conn.commit()
    except Exception as e:
        raise RuntimeError(f"Errore inizializzazione database: {e}") from e
