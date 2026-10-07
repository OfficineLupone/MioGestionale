import os
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

@st.cache_resource
def get_db_engine() -> Engine:
    """
    Crea e gestisce un motore di connessione SQLAlchemy con Connection Pooling.
    Grazie a @st.cache_resource la connessione viene riutilizzata 
    tra un click e l'altro, rendendo l'app immediata.
    """
    conn_str = st.secrets.get("postgres", {}).get("url") or os.getenv("DATABASE_URL")
    
    if not conn_str:
        user = st.secrets["postgres"]["user"]
        password = st.secrets["postgres"]["password"]
        host = st.secrets["postgres"]["host"]
        port = st.secrets["postgres"].get("port", 5432)
        db = st.secrets["postgres"]["database"]
        conn_str = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    
    # Assicura la connessione SSL richiesta da Neon
    if "sslmode" not in conn_str and "neon.tech" in conn_str:
        connector = "&" if "?" in conn_str else "?"
        conn_str += f"{connector}sslmode=require"

    return create_engine(
        conn_str,
        pool_size=5,
        max_overflow=10,
        pool_recycle=300,  # Ricicla le connessioni ogni 5 minuti
        pool_pre_ping=True  # Verifica la validità della connessione prima di usarla
    )

def init_db():
    """
    Crea le tabelle nello schema public, applica le migrazioni automatiche
    e crea gli indici per velocizzare le ricerche e i join.
    """
    engine = get_db_engine()
    with engine.begin() as conn:
        conn.execute(text("SET search_path TO public;"))

        # 1. Anagrafica Aziende
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.aziende (
                id SERIAL PRIMARY KEY,
                ragione_sociale VARCHAR(255) NOT NULL,
                piva VARCHAR(50),
                email VARCHAR(255),
                telefono VARCHAR(50),
                codice_sdi VARCHAR(20),
                referente VARCHAR(255)
            );
        """))

        # 2. Settori
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.settori (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) UNIQUE NOT NULL
            );
        """))

        # 3. Operatori
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.operatori (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(255) NOT NULL,
                settore_id INTEGER REFERENCES public.settori(id) ON DELETE SET NULL
            );
        """))

        # 4. Prodotti
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.prodotti (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(255) NOT NULL,
                macchina_gruppo_formato VARCHAR(255),
                disegno VARCHAR(255),
                materiale_trattamento VARCHAR(255),
                costo_interno NUMERIC(10, 2) DEFAULT 0.0,
                prezzo_vendita NUMERIC(10, 2) DEFAULT 0.0
            );
        """))

        # Rimuove vincoli NOT NULL restrittivi se presenti
        conn.execute(text("""
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
        """))

        # 5. Ore previste per settore su ogni prodotto
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.prodotto_ore_settori (
                id SERIAL PRIMARY KEY,
                prodotto_id INTEGER REFERENCES public.prodotti(id) ON DELETE CASCADE,
                settore_id INTEGER REFERENCES public.settori(id) ON DELETE CASCADE,
                ore NUMERIC(8, 2) DEFAULT 0.0
            );
        """))

        # 6. Preventivi
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.preventivi (
                id SERIAL PRIMARY KEY,
                azienda_id INTEGER REFERENCES public.aziende(id) ON DELETE CASCADE,
                prezzo_totale NUMERIC(10, 2) DEFAULT 0.0,
                stato VARCHAR(50) DEFAULT 'In attesa',
                data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        conn.execute(text("""
            ALTER TABLE public.preventivi 
            ADD COLUMN IF NOT EXISTS data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        """))

        # 7. Dettagli Preventivo
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.preventivo_dettagli (
                id SERIAL PRIMARY KEY,
                preventivo_id INTEGER REFERENCES public.preventivi(id) ON DELETE CASCADE,
                prodotto_id INTEGER REFERENCES public.prodotti(id) ON DELETE SET NULL,
                quantita INTEGER DEFAULT 1,
                prezzo_unitario NUMERIC(10, 2) DEFAULT 0.0,
                prezzo_totale NUMERIC(10, 2) DEFAULT 0.0
            );
        """))

        # 8. Lavorazioni ed Ore Effettive
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.lavorazioni (
                id SERIAL PRIMARY KEY,
                preventivo_id INTEGER REFERENCES public.preventivi(id) ON DELETE CASCADE,
                settore_id INTEGER REFERENCES public.settori(id) ON DELETE SET NULL,
                operatore_id INTEGER REFERENCES public.operatori(id) ON DELETE SET NULL,
                ore_effettive NUMERIC(8, 2) DEFAULT 0.0,
                note TEXT,
                data_registrazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Indici per ottimizzare la velocità delle query frequenti
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_preventivi_azienda ON public.preventivi(azienda_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_preventivi_stato ON public.preventivi(stato);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_prev_dettagli_prev ON public.preventivo_dettagli(preventivo_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ore_lavorate_prev ON public.ore_lavorate(preventivo_id);"))
