import os
import streamlit as st
import psycopg2

def _get_clean_db_url() -> str:
    db_url = st.secrets.get("DATABASE_URL", os.environ.get("DATABASE_URL", ""))
    if not db_url:
        raise ValueError("DATABASE_URL non trovato nei Secrets di Streamlit!")
    
    # 1. Corregge 'postgres://' in 'postgresql://'
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    # 2. Rimuove channel_binding se presente (causa errori di connessione su Neon con psycopg2)
    if "channel_binding=" in db_url:
        db_url = db_url.replace("&channel_binding=require", "").replace("?channel_binding=require", "")
        
    # 3. Assicura sslmode=require
    if "sslmode=" not in db_url:
        separator = "&" if "?" in db_url else "?"
        db_url = f"{db_url}{separator}sslmode=require"
        
    return db_url

def get_connection():
    db_url = _get_clean_db_url()
    conn = psycopg2.connect(db_url)
    return conn

def get_db_uri() -> str:
    return _get_clean_db_url()

def init_db():
    conn = get_connection()
    try:
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
                azienda_id INTEGER, 
                prodotto_id INTEGER, 
                quantita INTEGER, 
                prezzo_totale REAL, 
                ore_totali_stimate REAL, 
                stato VARCHAR(50) DEFAULT 'In attesa')''')
                
            # 7. Lavori
            c.execute('''CREATE TABLE IF NOT EXISTS lavori (
                id SERIAL PRIMARY KEY, 
                preventivo_id INTEGER, 
                settore_nome VARCHAR(255), 
                ore_effettive REAL, 
                note TEXT)''')
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
