import os
import psycopg2

def get_connection():
    # Recupera l'URL di connessione dai secret di Streamlit o dall'ambiente
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        import streamlit as st
        db_url = st.secrets["DATABASE_URL"]
    return psycopg2.connect(db_url)

def init_db():
    conn = get_connection()
    try:
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
                    settore_id INTEGER REFERENCES settori(id) ON DELETE CASCADE
                );
            """)
            
            # Tabella Prodotti
            c.execute("""
                CREATE TABLE IF NOT EXISTS prodotti (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(255) UNIQUE NOT NULL
                );
            """)

            # Aggiunta dinamica delle colonne mancanti sulla tabella prodotti
            colonne_mancanti = [
                ("materiale_trattamento", "TEXT DEFAULT ''"),
                ("macchina_gruppo_formato", "TEXT DEFAULT ''"),
                ("disegno", "TEXT DEFAULT ''"),
                ("costo_interno", "NUMERIC(10,2) DEFAULT 0.00"),
                ("prezzo_vendita", "NUMERIC(10,2) DEFAULT 0.00")
            ]
            
            for col_nome, col_tipo in colonne_mancanti:
                c.execute(f"""
                    ALTER TABLE prodotti 
                    ADD COLUMN IF NOT EXISTS {col_nome} {col_tipo};
                """)

            # Tabella relazione Ore Settori per Prodotto
            c.execute("""
                CREATE TABLE IF NOT EXISTS prodotto_ore_settori (
                    prodotto_id INTEGER REFERENCES prodotti(id) ON DELETE CASCADE,
                    settore_id INTEGER REFERENCES settori(id) ON DELETE CASCADE,
                    ore NUMERIC(10,2) DEFAULT 0.00,
                    PRIMARY KEY (prodotto_id, settore_id)
                );
            """)
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
