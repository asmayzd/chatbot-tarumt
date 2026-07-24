import configparser
import os
import secrets

import bcrypt
from psycopg2.extras import execute_values

from src.database.db_manager import get_db_connection

CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config.ini"))

STAFF_ACCOUNTS = [
    # (username, config_key, role, display_name)
    ("admin_tarumt", "admin_password", "admin", "Administrator"),
    ("analyst_tarumt", "analyst_password", "analyst", "Analyst BI"),
]


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _read_seed_config():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_PATH):
        config.read(CONFIG_PATH)
    return config


def seed_default_accounts():
    """Crée les comptes admin/analyst et un compte par client si absents.

    Aucun mot de passe en clair n'est écrit dans le code source : les valeurs
    de départ viennent de config.ini (ignoré par git) et, si elles manquent,
    sont générées aléatoirement puis affichées une seule fois en console.
    """
    config = _read_seed_config()
    seed_section = config["seed_accounts"] if config.has_section("seed_accounts") else {}

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Comptes admin / analyst (pas de customer_id associé)
        for username, config_key, role, display_name in STAFF_ACCOUNTS:
            cursor.execute("SELECT 1 FROM app_users WHERE username = %s;", (username,))
            if cursor.fetchone():
                continue

            password = seed_section.get(config_key)
            if not password:
                password = secrets.token_urlsafe(12)
                print(
                    f"⚠️  Aucun mot de passe défini pour '{username}' dans "
                    f"config.ini [seed_accounts] {config_key}. "
                    f"Mot de passe généré (à noter, affiché une seule fois) : {password}"
                )

            cursor.execute(
                "INSERT INTO app_users (username, password_hash, role, display_name) "
                "VALUES (%s, %s, %s, %s);",
                (username, _hash_password(password), role, display_name),
            )

        conn.commit()

        # 2. Un compte par client déjà présent dans customers, non encore provisionné
        default_password = seed_section.get("default_customer_password")
        if not default_password:
            default_password = secrets.token_urlsafe(12)
            print(
                "⚠️  Aucun mot de passe défini dans config.ini [seed_accounts] "
                f"default_customer_password. Mot de passe généré pour les clients "
                f"(à noter, affiché une seule fois) : {default_password}"
            )
        default_hash = _hash_password(default_password)

        cursor.execute(
            """
            SELECT c.customer_id, c.customer_name
            FROM customers c
            LEFT JOIN app_users u ON u.customer_id = c.customer_id
            WHERE u.user_id IS NULL;
            """
        )
        missing_customers = cursor.fetchall()

        if missing_customers:
            rows = [
                (customer_id, default_hash, "user", customer_name, customer_id)
                for customer_id, customer_name in missing_customers
            ]
            execute_values(
                cursor,
                "INSERT INTO app_users (username, password_hash, role, display_name, customer_id) "
                "VALUES %s ON CONFLICT (username) DO NOTHING;",
                rows,
                page_size=2000,
            )
            conn.commit()
            print(f"✅ {len(missing_customers)} compte(s) client provisionné(s) dans app_users.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur lors du seed des comptes : {str(e)}")
        raise e
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    seed_default_accounts()
