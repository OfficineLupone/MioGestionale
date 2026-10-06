import os
import psycopg2
from contextlib import contextmanager
import streamlit as st

@contextmanager
def get_connection():
    """
    Gestisce la connessione al database PostgreSQL ed imposta esplicitamente
    lo schema 'public' per evitare errori InvalidSchemaName.
    """
    conn = None
    try:
        conn_str = st.secrets.get("postgres", {}).get("url") or os.getenv("DATABASE_URL")
        
        if conn_str:
            conn = psycopg2.connect(conn_str)
        else:
            conn = psycopg2.connect(
                host=st.secrets["postgres"]["host"],
                database=st.secrets["postgres"]["database"],
                user=st.secrets["postgres"]["user"],
                password=st.secrets["postgres"]["password"],
                port=st.secrets["postgres"].get("port", 5432)
            )
        
        # Forza la sessione sullo schema standard 'public'
        with conn.cursor() as cur:
            cur.execute("SET search_path TO public;")
            
        yield conn
    except Exception as e:
        raise RuntimeError(f"Errore connessione database: {e}") from e
    finally:
        if conn:
            conn.close()

def init_db():
    """
    Crea le tabelle nello schema public ed applica le migrazioni automatiche.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO public;")

            # 1. Anagrafica Aziende
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.aziende (
                    id SERIAL PRIMARY KEY,
                    ragione_sociale VARCHAR(255) NOT NULL,
                    piva VARCHAR(50),
                    email VARCHAR(255),
                    telefono VARCHAR(50),
                    codice_sdi VARCHAR(20),
                    referente VARCHAR(255)
                );
            """)

            # 2. Settori
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.settori (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(100) UNIQUE NOT NULL
                );
            """)

            # 3. Operatori
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.operatori (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(255) NOT NULL,
                    settore_id INTEGER REFERENCES public.settori(id) ON DELETE SET NULL
                );
            """)

            # 4. Prodotti
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.prodotti (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(255) NOT NULL,
                    macchina_gruppo_formato VARCHAR(255),
                    disegno VARCHAR(255),
                    materiale_trattamento VARCHAR(255),
                    costo_interno NUMERIC(10, 2) DEFAULT 0.0,
                    prezzo_vendita NUMERIC(10, 2) DEFAULT 0.0
                );
            """)

            # Rimuove vincoli NOT NULL restrittivi da 'prodotti' se presenti da vecchie migrazioni
            cur.execute("""
                DO $$ 
                DECLARE 
                    r RECORD;
                BEGIN 
                    FOR r IN (
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                          AND table_name = 'prodotti' 
                          AND column_name NOT IN ('id', 'nome') 
                          AND is_nullable = 'NO'
                    ) LOOP
                        EXECUTE 'ALTER TABLE public.prodotti ALTER COLUMN ' || quote_ident(r.column_name) || ' DROP NOT NULL';
                    END LOOP;
                END $$;
            """)

            # 5. Ore previste per settore su ogni prodotto
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.prodotto_ore_settori (
                    id SERIAL PRIMARY KEY,
                    prodotto_id INTEGER REFERENCES public.prodotti(id) ON DELETE CASCADE,
                    settore_id INTEGER REFERENCES public.settori(id) ON DELETE CASCADE,
                    ore NUMERIC(8, 2) DEFAULT 0.0
                );
            """)

            # 6. Preventivi
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.preventivi (
                    id SERIAL PRIMARY KEY,
                    azienda_id INTEGER REFERENCES public.aziende(id) ON DELETE CASCADE,
                    prezzo_totale NUMERIC(10, 2) DEFAULT 0.0,
                    stato VARCHAR(50) DEFAULT 'In attesa',
                    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                ALTER TABLE public.preventivi 
                ADD COLUMN IF NOT EXISTS data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            """)

            # 7. Dettagli Preventivo
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.preventivo_dettagli (
                    id SERIAL PRIMARY KEY,
                    preventivo_id INTEGER REFERENCES public.preventivi(id) ON DELETE CASCADE,
                    prodotto_id INTEGER REFERENCES public.prodotti(id) ON DELETE SET NULL,
                    quantita INTEGER DEFAULT 1,
                    prezzo_unitario NUMERIC(10, 2) DEFAULT 0.0,
                    prezzo_totale NUMERIC(10, 2) DEFAULT 0.0
                );
            """)

            # 8. Lavorazioni ed Ore Effettive
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.lavorazioni (
                    id SERIAL PRIMARY KEY,
                    preventivo_id INTEGER REFERENCES public.preventivi(id) ON DELETE CASCADE,
                    settore_id INTEGER REFERENCES public.settori(id) ON DELETE SET NULL,
                    operatore_id INTEGER REFERENCES public.operatori(id) ON DELETE SET NULL,
                    ore_effettive NUMERIC(8, 2) DEFAULT 0.0,
                    note TEXT,
                    data_registrazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            conn.commit()
