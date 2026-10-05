import os
import streamlit as st
import psycopg2

def get_connection():
    db_url = st.secrets.get("DATABASE_URL", os.environ.get("DATABASE_URL"))
    if not db_url:
        raise ValueError("DATABASE_URL non trovato nei Secrets di Streamlit!")
    return psycopg2.connect(db_url)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Tabella Settori
    c.execute('''CREATE TABLE IF NOT EXISTS settori (
        id SERIAL PRIMARY KEY, 
        nome VARCHAR(255) UNIQUE NOT NULL)''')
        
    # 2. Tabella Operatori
    c.execute('''CREATE TABLE IF NOT EXISTS operatori (
        id SERIAL PRIMARY KEY,
        nome VARCHAR(255) NOT NULL,
        settore_id INTEGER NOT NULL REFERENCES settori(id) ON DELETE CASCADE)''')

    # 3. Tabella Prodotti
    c.execute('''CREATE TABLE IF NOT EXISTS prodotti (
        id SERIAL PRIMARY KEY, 
        nome VARCHAR(255) UNIQUE NOT NULL, 
        materiale_trattamento TEXT,
        macchina_gruppo_formato TEXT,
        disegno TEXT,
        costo_interno REAL NOT NULL DEFAULT 0.0, 
        prezzo_vendita REAL NOT NULL DEFAULT 0.0)''')
        
    # 4. Tabella Ore Settori per Prodotto
    c.execute('''CREATE TABLE IF NOT EXISTS prodotto_ore_settori (
        prodotto_id INTEGER REFERENCES prodotti(id) ON DELETE CASCADE,
        settore_id INTEGER REFERENCES settori(id) ON DELETE CASCADE,
        ore REAL NOT NULL DEFAULT 0.0,
        PRIMARY KEY (prodotto_id, settore_id))''')

    # 5. Tabella Aziende
    c.execute('''CREATE TABLE IF NOT EXISTS aziende (
        id SERIAL PRIMARY KEY, 
        ragione_sociale VARCHAR(255) UNIQUE NOT NULL, 
        piva VARCHAR(50), 
        email VARCHAR(255))''')
        
    # 6. Tabella Preventivi
    c.execute('''CREATE TABLE IF NOT EXISTS preventivi (
        id SERIAL PRIMARY KEY, 
        azienda_id INTEGER, 
        prodotto_id INTEGER, 
        quantita INTEGER, 
        prezzo_totale REAL, 
        ore_totali_stimate REAL, 
        stato VARCHAR(50) DEFAULT 'In attesa')''')
        
    # 7. Tabella Lavori
    c.execute('''CREATE TABLE IF NOT EXISTS lavori (
        id SERIAL PRIMARY KEY, 
        preventivo_id INTEGER, 
        settore_nome VARCHAR(255), 
        ore_effettive REAL, 
        note TEXT)''')
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
