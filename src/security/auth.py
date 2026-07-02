"""
Module Cybersécurité — Authentification & gestion des rôles.

Auth simple par login/mot de passe (hash SHA-256 + sel) et token de session.
Trois rôles : admin, analyste, utilisateur.

Contrat exposé :
    authenticate(username, password) -> dict  (avec token si succès)
    verify_token(token) -> dict | None
    get_role(username) -> str | None
    can_access(role, resource) -> bool
"""
import hashlib
import secrets
import time

# --- Base utilisateurs (en prod : base de données + hash bcrypt) ------------
# mot de passe stocké sous forme sha256(sel + mot_de_passe)
_SEL = "s3l_du_projet_chatbot"

def _hash(mot_de_passe: str) -> str:
    return hashlib.sha256((_SEL + mot_de_passe).encode()).hexdigest()

# Comptes de démonstration
USERS = {
    "admin":    {"password": _hash("admin123"),    "role": "admin"},
    "besma":    {"password": _hash("analyste123"), "role": "analyste"},
    "invite":   {"password": _hash("invite123"),   "role": "utilisateur"},
}

# --- Matrice de contrôle d'accès (rôle -> ressources autorisées) ------------
ACCESS_MATRIX = {
    "admin":       {"kpi", "documents", "clients_pii", "logs", "config", "dashboard"},
    "analyste":    {"kpi", "documents", "dashboard"},
    "utilisateur": {"kpi_public", "documents"},
}

# Sessions actives : token -> {username, role, expire}
_SESSIONS = {}
_TTL = 3600  # durée de vie d'un token en secondes (1h)


def authenticate(username: str, password: str) -> dict:
    """Vérifie les identifiants et renvoie un token de session si succès."""
    user = USERS.get((username or "").lower())
    if not user or user["password"] != _hash(password or ""):
        return {"success": False, "reason": "Identifiants invalides",
                "token": None, "role": None}
    token = secrets.token_hex(16)
    _SESSIONS[token] = {"username": username.lower(),
                        "role": user["role"],
                        "expire": time.time() + _TTL}
    return {"success": True, "reason": "Connexion réussie",
            "token": token, "role": user["role"]}


def verify_token(token: str):
    """Renvoie la session si le token est valide et non expiré, sinon None."""
    sess = _SESSIONS.get(token)
    if not sess:
        return None
    if time.time() > sess["expire"]:
        _SESSIONS.pop(token, None)
        return None
    return sess


def logout(token: str) -> bool:
    return _SESSIONS.pop(token, None) is not None


def get_role(username: str):
    user = USERS.get((username or "").lower())
    return user["role"] if user else None


def can_access(role: str, resource: str) -> bool:
    """Vérifie si un rôle a le droit d'accéder à une ressource."""
    return resource in ACCESS_MATRIX.get(role, set())


if __name__ == "__main__":
    r = authenticate("besma", "analyste123")
    print("Auth besma :", r["success"], r["role"])
    print("Analyste -> clients_pii :", can_access("analyste", "clients_pii"))
    print("Admin    -> clients_pii :", can_access("admin", "clients_pii"))
    print("Token valide :", verify_token(r["token"]) is not None)
