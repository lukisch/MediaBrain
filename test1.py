import sqlite3
from pathlib import Path

# Pfad zur DB (muss im selben Ordner liegen wie deine Skripte)
db_path = Path("media_brain.db")

if not db_path.exists():
    print("❌ FEHLER: Keine Datenbank gefunden!")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"--- Inhalt der Datenbank ({db_path}) ---")
    try:
        cursor.execute("SELECT id, title, source, type FROM media_items")
        rows = cursor.fetchall()
        
        if not rows:
            print("⚠️ Die Tabelle ist LEER.")
        else:
            for row in rows:
                print(f"ID: {row[0]} | Titel: {row[1]} | Quelle: {row[2]} | Typ: {row[3]}")
                
    except Exception as e:
        print(f"Fehler beim Lesen: {e}")
    
    conn.close()