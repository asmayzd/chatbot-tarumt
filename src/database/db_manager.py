import sqlite3
import os

DB_PATH = "data/superstore_bi.db"

def get_db_connection():
    """Établit une connexion à la base SQLite en forçant le respect des clés étrangères (FK)."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    # CRUCIAL : SQLite désactive les clés étrangères par défaut. On force l'activation ici.
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Lit le fichier schema.sql et initialise l'arborescence des tables DDL en 3NF."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    
    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            ddl_script = f.read()
        
        with get_db_connection() as conn:
            conn.executescript(ddl_script)
            conn.commit()
        print("💡 Base de données relationnelle Superstore initialisée avec succès (3NF).")
    else:
        print(f"⚠️ Erreur : Impossible de trouver le schéma DDL à l'emplacement : {schema_path}")