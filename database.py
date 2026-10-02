import sqlite3

def init_db():
    conn = sqlite3.connect('gestionale.db')
    c = conn.cursor()
    
    # Tabelle del gestionale
    c.execute('''CREATE TABLE IF NOT EXISTS settori (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE NOT NULL)''')
    
    # Inserisci i dati iniziali SOLO se la tabella è totalmente vuota (primo avvio in assoluto)
    c.execute("SELECT COUNT(*) FROM settori")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO settori (nome) VALUES ('Progettazione')")
        c.execute("INSERT INTO settori (nome) VALUES ('Lavorazione')")
        c.execute("INSERT INTO settori (nome) VALUES ('Assemblaggio')")
    
    c.execute('''CREATE TABLE IF NOT EXISTS prodotti (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE NOT NULL, 
        ore_lavorazione REAL NOT NULL, costo_interno REAL NOT NULL, prezzo_vendita REAL NOT NULL)''')
        
    c.execute('''CREATE TABLE IF NOT EXISTS aziende (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ragione_sociale TEXT UNIQUE NOT NULL, piva TEXT, email TEXT)''')
        
    c.execute('''CREATE TABLE IF NOT EXISTS preventivi (
        id INTEGER PRIMARY KEY AUTOINCREMENT, azienda_id INTEGER, prodotto_id INTEGER, 
        quantita INTEGER, prezzo_totale REAL, ore_totali_stimate REAL, stato TEXT DEFAULT 'In attesa')''')
        
    c.execute('''CREATE TABLE IF NOT EXISTS lavori (
        id INTEGER PRIMARY KEY AUTOINCREMENT, preventivo_id INTEGER, settore_nome TEXT, ore_effettive REAL, note TEXT)''')
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
