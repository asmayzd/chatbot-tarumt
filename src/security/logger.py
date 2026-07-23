import logging
import os

# S'assurer que le dossier pour les journaux de sécurité existe
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, "security_audit.log")

# Configuration du logger
logger = logging.getLogger("SecurityAudit")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

def log_security_event(username: str, role: str, action: str, status: str, details: str = ""):
    """Enregistre un événement de sécurité au format standardisé (fichier + DB)."""
    message = f"User: {username} | Role: {role} | Action: {action} | Status: {status} | Details: {details}"

    if status in ["FAILED", "BLOCKED", "CRITICAL"]:
        logger.warning(message)
    else:
        logger.info(message)

    _log_to_db(username, role, action, status, details)


def _log_to_db(username: str, role: str, action: str, status: str, details: str):
    """Miroir en base pour le dashboard cybersécurité admin.

    Best-effort : une base indisponible ne doit jamais faire échouer une
    requête utilisateur, le fichier .log ci-dessus reste la source de vérité
    de secours.
    """
    try:
        # Import différé : évite tout risque de dépendance circulaire au chargement.
        from src.database.db_manager import get_db_connection

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO security_events (username, role, action, status, details) "
                "VALUES (%s, %s, %s, %s, %s);",
                (username, role, action, status, details),
            )
            conn.commit()
            cursor.close()
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"Impossible d'écrire l'événement de sécurité en base : {e}")