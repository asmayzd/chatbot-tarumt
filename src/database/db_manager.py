import os
import configparser
import psycopg2
from psycopg2.extras import RealDictCursor

def check_and_auto_ingest():
    """Vérifie si la base PostgreSQL est peuplée. Si elle est vide, lance l'ingestion automatiquement."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. On initialise d'abord les structures si elles n'existent pas
        init_db()
        
        # 2. On vérifie si la table 'customers' contient au moins une ligne
        cursor.execute("SELECT COUNT(*) FROM customers;")
        count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()

        if count == 0:
            print("⚡ Base de données PostgreSQL vide détectée. Lancement automatique de l'ingestion...")
            # Import différé pour éviter les imports circulaires
            from src.database.ingest_data import populate_database
            populate_database()
        else:
            print(f"✅ Base de données PostgreSQL déjà opérationnelle ({count} clients détectés). Pas d'ingestion nécessaire.")

    except Exception as e:
        print(f"⚠️ Erreur lors de la vérification/ingestion automatique : {str(e)}")

def get_db_connection():
    """Établit une connexion à PostgreSQL en lisant les identifiants depuis le fichier config.ini."""
    try:
        # Initialisation du parser de configuration
        config = configparser.ConfigParser()
        
        # On cherche le fichier config.ini à la racine du projet
        # Si ton fichier est ailleurs, ajuste le chemin relatif ici
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config.ini"))
        
        if not os.path.exists(config_path):
            # Test alternatif au cas où le script est exécuté depuis la racine
            config_path = "config.ini"
            
        config.read(config_path)

        # Extraction des paramètres depuis la section [postgresql] du fichier config.ini
        db_host = config.get("postgresql", "host", fallback="127.0.0.1")
        db_port = config.get("postgresql", "port", fallback="5432")
        db_name = config.get("postgresql", "database", fallback="postgres")
        db_user = config.get("postgresql", "user", fallback="postgres")
        db_password = config.get("postgresql", "password", fallback=None)

        if not db_password:
            raise ValueError(f"Le paramètre 'password' est manquant dans la section [postgresql] du fichier {config_path}")

        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        return conn
    except Exception as e:
        print(f"❌ Erreur critique lors de la connexion à PostgreSQL : {str(e)}")
        raise e

def init_db():
    """Lit le fichier schema.sql local et initialise les structures sur PostgreSQL."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    
    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            ddl_script = f.read()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(ddl_script)
            conn.commit()
            print("💡 Base de données PostgreSQL initialisée avec succès (Schéma 3NF).")
        except Exception as e:
            conn.rollback()
            print(f"❌ Erreur lors de l'exécution du schéma DDL : {str(e)}")
        finally:
            cursor.close()
            conn.close()
    else:
        print(f"⚠️ Erreur : Impossible de trouver le schéma DDL à l'emplacement : {schema_path}")