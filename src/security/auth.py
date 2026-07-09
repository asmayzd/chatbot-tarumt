import hashlib
import streamlit as st
from src.security.logger import log_security_event

# Base de données simulée (Customer ID / Username: {Mot de passe, Nom, Rôle})
# Contient les 3 rôles de base et tes 3 clients réels issus du fichier superstore.csv
USER_DB = {
    "admin_tarumt": {
        "password": hashlib.sha256("admin123".encode()).hexdigest(),
        "customer_name": "Administrator",
        "role": "admin"
    },
    "analyst_tarumt": {
        "password": hashlib.sha256("analyst123".encode()).hexdigest(),
        "customer_name": "Analyst BI",
        "role": "analyst"
    },
    "user_tarumt": {
        "password": hashlib.sha256("user123".encode()).hexdigest(),
        "customer_name": "Generic User",
        "role": "user"
    },
    # Nouveaux profils clients réels de ta base de données
    "CS-121304": {
        "password": hashlib.sha256("user123".encode()).hexdigest(),
        "customer_name": "Chad Sievert",
        "role": "user"
    },
    "AP-109154": {
        "password": hashlib.sha256("user123".encode()).hexdigest(),
        "customer_name": "Arthur Prichep",
        "role": "user"
    },
    "JF-154904": {
        "password": hashlib.sha256("user123".encode()).hexdigest(),
        "customer_name": "Jeremy Farry",
        "role": "user"
    }
}


def verify_credentials(username, password):
    """Vérifie la validité des identifiants entrés et retourne (role, customer_name)."""
    if username in USER_DB:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        if USER_DB[username]["password"] == hashed_password:
            return USER_DB[username]["role"], USER_DB[username]["customer_name"]
    return None, None


def render_login_form():
    """Affiche l'interface graphique du formulaire de connexion."""
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
                    Please login with your credentials or Customer ID (e.g., CS-121304).
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.form("login_form"):
            username = st.text_input("Customer ID / Username", placeholder="ex. CS-121304")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submit = st.form_submit_button("Se connecter", use_container_width=True)

            if submit:
                role, customer_name = verify_credentials(username, password)
                if role:
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username
                    st.session_state["customer_name"] = customer_name
                    st.session_state["role"] = role

                    log_security_event(username, role, "login", "SUCCESS", f"User {customer_name} connected")
                    st.success(f"Bienvenue {customer_name} ({role}) !")
                    st.rerun()
                else:
                    log_security_event(username, "UNKNOWN", "login", "FAILED", f"Échec de connexion")
                    st.error("Invalid Customer ID or Password.")
