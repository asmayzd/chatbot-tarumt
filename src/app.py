"""
Application intégrée — Chatbot E-commerce sécurisé.

Assemble les 3 modules :
  - Cybersécurité : login/rôles, filtre de requêtes, logs
  - Data Science / ML : moteur du chatbot
  - BI & Analytics : dashboard KPI

Lancer :  streamlit run src/app.py

Comptes de démonstration :
  admin  / admin123      (accès complet : KPI, PII, logs)
  besma  / analyste123   (KPI + dashboard, pas de PII)
  invite / invite123     (accès limité)
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import streamlit as st

from src.security import auth, security_rules, logs
from src.chatbot.chatbot_engine import chatbot_response
from src.analytics import dashboard

st.set_page_config(page_title="Chatbot E-commerce sécurisé",
                   page_icon="🤖", layout="wide")


# --- Écran de connexion -----------------------------------------------------
def ecran_login():
    st.title("🔐 Connexion")
    st.caption("Chatbot intelligent sécurisé — analyse de données e-commerce")
    with st.form("login"):
        u = st.text_input("Utilisateur")
        p = st.text_input("Mot de passe", type="password")
        ok = st.form_submit_button("Se connecter")
    if ok:
        res = auth.authenticate(u, p)
        if res["success"]:
            st.session_state.token = res["token"]
            st.session_state.role = res["role"]
            st.session_state.user = u.lower()
            st.rerun()
        else:
            st.error(res["reason"])
    with st.expander("Comptes de démonstration"):
        st.markdown(
            "- **admin** / `admin123` — accès complet (KPI, données clients, logs)\n"
            "- **besma** / `analyste123` — KPI + dashboard\n"
            "- **invite** / `invite123` — accès limité"
        )


# --- Onglet Chatbot ---------------------------------------------------------
def onglet_chatbot():
    st.header("🤖 Chatbot")
    role, user = st.session_state.role, st.session_state.user

    if "historique" not in st.session_state:
        st.session_state.historique = []

    with st.expander("💡 Exemples de questions"):
        st.markdown(
            "- Quel est le chiffre d'affaires total ?\n"
            "- Quels sont les produits les plus vendus ?\n"
            "- Quel mois a eu les meilleures ventes ?\n"
            "- Combien de clients sont inactifs ?\n"
            "- Y a-t-il des anomalies dans les ventes ?\n"
            "- Quels sont les délais de livraison ?"
        )

    for msg in st.session_state.historique:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    question = st.chat_input("Posez votre question...")
    if question:
        st.session_state.historique.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        # 1) Sécurité
        secu = security_rules.check_security(question, role)
        if not secu["allowed"]:
            reponse = f"⛔ **Requête bloquée** — {secu['reason']}"
            logs.log_interaction(user, role, question, False,
                                 secu["risk_level"], secu["category"], reponse)
        else:
            # 2) Chatbot
            rep = chatbot_response(question, role)
            src = f"\n\n*Source : {rep['source']}*" if rep["source"] else ""
            reponse = rep["answer"] + src
            # 3) Logs
            logs.log_interaction(user, role, question, True,
                                 secu["risk_level"], rep["category"], rep["answer"])

        st.session_state.historique.append({"role": "assistant", "content": reponse})
        with st.chat_message("assistant"):
            st.markdown(reponse)


# --- Onglet Logs (admin) ----------------------------------------------------
def onglet_logs():
    st.header("📜 Journal des conversations")
    if not auth.can_access(st.session_state.role, "logs"):
        st.warning("Accès réservé à l'administrateur.")
        return
    df = logs.read_logs()
    if df.empty:
        st.info("Aucune interaction enregistrée.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("Télécharger les logs (CSV)",
                           df.to_csv(index=False).encode("utf-8"),
                           "logs_conversations.csv", "text/csv")


# --- Application principale --------------------------------------------------
def main():
    if "token" not in st.session_state or not auth.verify_token(st.session_state.token):
        ecran_login()
        return

    with st.sidebar:
        st.success(f"Connecté : **{st.session_state.user}**")
        st.caption(f"Rôle : {st.session_state.role}")
        if st.button("Se déconnecter"):
            auth.logout(st.session_state.token)
            for k in ["token", "role", "user", "historique"]:
                st.session_state.pop(k, None)
            st.rerun()

    onglets = ["🤖 Chatbot", "📊 Dashboard"]
    if auth.can_access(st.session_state.role, "logs"):
        onglets.append("📜 Logs")
    tabs = st.tabs(onglets)

    with tabs[0]:
        onglet_chatbot()
    with tabs[1]:
        dashboard.render_dashboard(st, logs.read_logs())
    if len(tabs) > 2:
        with tabs[2]:
            onglet_logs()


if __name__ == "__main__":
    main()
