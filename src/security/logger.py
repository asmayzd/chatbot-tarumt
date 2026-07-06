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
    """Enregistre un événement de sécurité au format standardisé."""
    message = f"User: {username} | Role: {role} | Action: {action} | Status: {status} | Details: {details}"
    
    if status in ["FAILED", "BLOCKED"]:
        logger.warning(message)
    else:
        logger.info(message)