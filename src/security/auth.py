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
    """Affiche l'interface graphique du formulaire de connexion (design moderne)."""
    # Carte de connexion centrée
    left, center, right = st.columns([1, 1.3, 1])

    with center:
        st.markdown(
            """
            <div style="text-align:center; margin-top:8vh; margin-bottom:18px;">
                <div style="font-size:3rem;">🔐</div>
                <h1 style="margin:6px 0 2px; font-size:1.6rem; font-weight:800; color:#4f46e5;">
                    TARUMT System
                </h1>
                <p style="color:#6b7280; margin:0;">
                    Authentifiez-vous pour activer le modèle Gemini et le tableau de bord BI.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.form("login_form"):
            username = st.text_input("Identifiant utilisateur", placeholder="ex. analyst_tarumt")
            password = st.text_input("Mot de passe", type="password", placeholder="••••••••")
            submit = st.form_submit_button("Se connecter", use_container_width=True)

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
