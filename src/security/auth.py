import bcrypt
import streamlit as st
from src.database.db_manager import get_db_connection
from src.security.logger import log_security_event


def verify_credentials(username, password):
    """Vérifie les identifiants contre la table app_users (mots de passe bcrypt).

    Retourne (role, display_name, user_id) si valide, sinon (None, None, None).
    Les identifiants ne sont plus jamais codés en dur dans le code source :
    ils vivent uniquement en base, provisionnés par src.database.seed_users.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, password_hash, role, display_name "
            "FROM app_users WHERE username = %s;",
            (username,),
        )
        row = cursor.fetchone()
        cursor.close()
    finally:
        conn.close()

    if not row:
        return None, None, None

    user_id, password_hash, role, display_name = row
    if bcrypt.checkpw(password.encode(), password_hash.encode()):
        return role, display_name, user_id
    return None, None, None


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
                role, customer_name, user_id = verify_credentials(username, password)
                if role:
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username
                    st.session_state["customer_name"] = customer_name
                    st.session_state["role"] = role
                    st.session_state["user_id"] = user_id

                    log_security_event(username, role, "login", "SUCCESS", f"User {customer_name} connected")
                    st.success(f"Welcome {customer_name} ({role}) !")
                    st.rerun()
                else:
                    log_security_event(username, "UNKNOWN", "login", "FAILED", f"Échec de connexion")
                    st.error("Invalid Customer ID or Password.")
