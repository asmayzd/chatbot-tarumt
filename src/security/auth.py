import hashlib
import streamlit as st
from src.security.logger import log_security_event

# Base de données simulée (Identifiant: {Mots de passe hachés, Rôle affecté})
# Mots de passe valides : 'admin123', 'analyst123', 'user123'
USER_DB = {
    "admin_tarumt": {
        "password": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "admin"
    },
    "analyst_tarumt": {
        "password": hashlib.sha256("analyst123".encode()).hexdigest(),
        "role": "analyst"
    },
    "user_tarumt": {
        "password": hashlib.sha256("user123".encode()).hexdigest(),
        "role": "user"
    }
}

def verify_credentials(username, password):
    """Vérifie la validité des identifiants entrés."""
    if username in USER_DB:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        if USER_DB[username]["password"] == hashed_password:
            return USER_DB[username]["role"]
    return None

def render_login_form():
    """Affiche l'interface graphique du formulaire de connexion."""
    st.title(" Arden 🔐 Connexion TARUMT System")
    st.markdown("Veuillez vous authentifier pour activer le modèle LLM Gemini et le tableau de bord BI.")
    
    with st.form("login_form"):
        username = st.text_input("Identifiant utilisateur")
        password = st.text_input("Mot de passe", type="password")
        submit = st.form_submit_button("Se connecter")
        
        if submit:
            role = verify_credentials(username, password)
            if role:
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.session_state["role"] = role
                
                log_security_event(username, role, "login", "SUCCESS", "Connexion réussie au tableau de bord")
                st.success(f"Bienvenue {username} ({role}) !")
                st.rerun()
            else:
                log_security_event(username, "UNKNOWN", "login", "FAILED", f"Échec de connexion pour l'identifiant : {username}")
                st.error("Identifiant ou mot de passe incorrect.")