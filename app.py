import streamlit as st
import pandas as pd
import sys
import os
import configparser

# Intégration des tables SQL
from src.database.db_manager import init_db
init_db()

# Load confidential keys from the local config.ini file safely
config = configparser.ConfigParser()
config_file = "config.ini"

if os.path.exists(config_file):
    config.read(config_file)
    if "API_KEYS" in config and "GEMINI_API_KEY" in config["API_KEYS"]:
        os.environ["GEMINI_API_KEY"] = config["API_KEYS"]["GEMINI_API_KEY"]

# Add root directory to path for imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# --- SÉCURITÉ : Importations des modules de contrôle ---
from src.security.auth import render_login_form
from src.security.logger import log_security_event
from src.security.guardrails import (
    detect_prompt_injection, 
    handle_security_violation, 
    get_secured_dataframe, 
    check_sql_outcome_security,
    detect_cross_user_violation
)

# Page Configuration
st.set_page_config(
    page_title="TARUMT Chatbot & BI Dashboard",
    page_icon="🤖",
    layout="wide"
)

# ============================================================
#  DICTIONNAIRE DE TRADUCTION (Dictionnaire Multilingue)
# ============================================================
TRANSLATIONS = {
    "EN": {
        "sql_active": "🟢 Active (Gemini)",
        "sql_inactive": "🔴 Inactive",
        "bi_granted": "🟢 Access Granted",
        "bi_locked": "🔒 Restricted (analyst / admin)",
        "security_warn": "Security Warnings",
        "logout": "🚪 Log out",
        "hero_desc": "Ask your questions about sales, profits, and delivery times in natural language.",
        "connected": "Connected",
        "sales_sub": "global turnover",
        "profit_sub": "global net profit",
        "anomaly_warn": "needs monitoring",
        "anomaly_ok": "no critical alerts",
        "anomaly_expander": "View financial anomaly details",
        "anomaly_sales": "High sales with negative profit",
        "anomaly_disc": "High discount with negative profit",
        "bi_restricted_info": "🔒 The BI Analytics Dashboard is reserved for **analyst** and **admin** roles. However, you can still ask your questions to the assistant below.",
        "sql_expander": "🔍 Details — SQL query used",
        "welcome": "Hello! I am your TARUMT data assistant. Try asking: 'Top 5 countries by sales' or 'profit by category'.",
        "chat_placeholder": "Type your question here...",
        "spinner": "Analyzing..."
    },
    "FR": {
        "sql_active": "🟢 Actif (Gemini)",
        "sql_inactive": "🔴 Inactif",
        "bi_granted": "🟢 Accès Autorisé",
        "bi_locked": "🔒 Réservé (analyst / admin)",
        "security_warn": "Avertissements de Sécurité",
        "logout": "🚪 Se déconnecter",
        "hero_desc": "Posez vos questions sur les ventes, les profits et les délais de livraison en langage naturel.",
        "connected": "Connecté",
        "sales_sub": "chiffre d'affaires global",
        "profit_sub": "bénéfice net global",
        "anomaly_warn": "à surveiller",
        "anomaly_ok": "aucune alerte critique",
        "anomaly_expander": "Voir le détail des anomalies financières",
        "anomaly_sales": "Ventes élevées avec profit négatif",
        "anomaly_disc": "Remises élevées avec profit négatif",
        "bi_restricted_info": "🔒 Le tableau de bord BI Analytics est réservé aux rôles **analyst** et **admin**. Vous pouvez néanmoins poser vos questions à l'assistant ci-dessous.",
        "sql_expander": "🔍 Détails — requête SQL utilisée",
        "welcome": "Bonjour ! Je suis votre assistant data TARUMT. Essayez par exemple : 'Top 5 des pays par ventes' ou 'profit par catégorie'.",
        "chat_placeholder": "Posez votre question ici...",
        "spinner": "Analyse en cours..."
    }
}

# ============================================================
#  STYLE GLOBAL — interface moderne (CSS injecté)
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Inter', sans-serif;
}
.stApp {
    background: linear-gradient(180deg, #f7f8fc 0%, #eef1f8 100%);
}

/* ---- Hero header ---- */
.hero {
    background: linear-gradient(120deg, #4f46e5 0%, #7c3aed 55%, #9333ea 100%);
    border-radius: 20px;
    padding: 26px 30px;
    color: #fff;
    box-shadow: 0 12px 30px rgba(79,70,229,0.25);
    margin-bottom: 22px;
}
.hero h1 { margin: 0; font-size: 1.7rem; font-weight: 800; letter-spacing: -0.02em; }
.hero p  { margin: 6px 0 0; opacity: 0.9; font-size: 0.95rem; }
.role-badge {
    display: inline-block; margin-top: 12px; padding: 4px 14px;
    background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.35);
    border-radius: 999px; font-size: 0.8rem; font-weight: 600; letter-spacing: 0.02em;
}

/* ---- KPI cards ---- */
.kpi-card {
    background: #ffffff; border-radius: 18px; padding: 20px 22px;
    box-shadow: 0 6px 20px rgba(17,24,39,0.06); border: 1px solid #eef0f6;
    height: 100%;
}
.kpi-icon {
    width: 44px; height: 44px; border-radius: 12px; display: flex;
    align-items: center; justify-content: center; font-size: 1.3rem; margin-bottom: 12px;
}
.kpi-label { color: #6b7280; font-size: 0.82rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.kpi-value { color: #111827; font-size: 1.7rem; font-weight: 800; margin-top: 2px; letter-spacing: -0.02em; }
.kpi-sub   { color: #9ca3af; font-size: 0.78rem; margin-top: 4px; }

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {
    background: #ffffff; border-right: 1px solid #eef0f6;
}
.profile-card {
    background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 100%);
    border: 1px solid #e0e7ff; border-radius: 14px; padding: 14px 16px; margin-bottom: 8px;
}
.profile-name { font-weight: 700; color: #4338ca; font-size: 0.95rem; }
.profile-role { color: #6d28d9; font-size: 0.78rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }

/* ---- Chat bubbles ---- */
.stChatMessage {
    border-radius: 16px; padding: 4px 6px;
}

/* ---- Buttons ---- */
.stButton > button {
    border-radius: 10px; font-weight: 600; border: 1px solid #e5e7eb;
}

/* ---- Expander (SQL detail) ---- */
[data-testid="stExpander"] {
    border-radius: 12px; border: 1px solid #e5e7eb; overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

# --- SÉCURITÉ : Vérification de la Session d'Authentification (RBAC) ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    render_login_form()
    st.stop()

current_user = st.session_state["username"]
current_name = st.session_state.get("customer_name", "User")
user_role = st.session_state["role"]

BI_ALLOWED_ROLES = ("admin", "analyst")
can_view_bi = user_role in BI_ALLOWED_ROLES

# Secure imports from the project modules
try:
    from src.data_science.chatbot_engine import ChatbotEngine
    from src.bi_analytics.kpi_analyzer import KPIAnalyzer
    from src.bi_analytics.anomaly_detector import AnomalyDetector
    from src.bi_analytics.sql_agent import SQLAgent
    from src.data_science.data_loader import DataLoader
    from src.data_science.data_cleaner import DataCleaner
    MODULES_AVAILABLE = True
except ImportError as e:
    MODULES_AVAILABLE = False
    IMPORT_ERROR = str(e)

# --- AI Integration (Google GenAI Gemini) ---
USE_GEMINI_AI = False
if "GEMINI_API_KEY" in os.environ:
    try:
        from google import genai
        client = genai.Client()
        USE_GEMINI_AI = True
    except ImportError:
        pass

# --- Cached Components Initialisation ---
@st.cache_resource
def init_components():
    if not MODULES_AVAILABLE:
        return None, None, None, None

    loader = DataLoader(file_path="data/superstore.csv")
    df = loader.load_csv()
    cleaner = DataCleaner(df)
    df_clean = cleaner.clean()

    kpi = KPIAnalyzer(df_clean)
    anomaly = AnomalyDetector(df_clean)

    sql_agent = None
    if USE_GEMINI_AI:
        sql_agent = SQLAgent(db_path="data/superstore_bi.db").setup()

    return kpi, anomaly, sql_agent, df_clean

if MODULES_AVAILABLE:
    kpi_analyzer, anomaly_detector, sql_agent, df_clean = init_components()
    
    # --- CYBERSECURITE : RLS Filtrage dynamique par ID de session ---
    secured_df = get_secured_dataframe(df_clean, user_role, current_user)
    engine = ChatbotEngine(secured_df)
else:
    st.error(f"Failed to import project modules: {IMPORT_ERROR}")


def kpi_card(icon, label, value, accent_bg, accent_fg, sub=""):
    """Return the HTML for a modern KPI card."""
    return f"""
    <div class="kpi-card">
        <div class="kpi-icon" style="background:{accent_bg};color:{accent_fg};">{icon}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>
    """


# ============================================================
#  SIDEBAR
# ============================================================
with st.sidebar:
    # Sélecteur de langue minimal et efficace
    selected_lang = st.selectbox("🌐 Language / Langue", ["EN", "FR"], index=0)
    lang = TRANSLATIONS[selected_lang]

    st.write("")
    st.markdown(
        f'<div class="profile-card">'
        f'<div class="profile-name">👤 {current_name}</div>'
        f'<div class="profile-role">{user_role} ({current_user})</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    st.caption(f"🤖 SQL Agent: {lang['sql_active'] if (MODULES_AVAILABLE and sql_agent) else lang['sql_inactive']}")

    if can_view_bi:
        st.caption(f"📊 BI Analytics: {lang['bi_granted']}")
    else:
        st.caption(f"📊 BI Analytics: {lang['bi_locked']}")

    # Récupération propre du compteur de violations
    violations_count = st.session_state.get("security_violations", 0)
    if violations_count > 0:
        st.markdown(f"⚠️ **{lang['security_warn']}:** `{violations_count}/3`")

    st.write("---")

    if st.button(lang["logout"], use_container_width=True):
        log_security_event(current_user, user_role, "logout", "SUCCESS", "Voluntary disconnection")
        st.session_state["authenticated"] = False
        st.session_state["security_violations"] = 0
        st.rerun()


# ============================================================
#  HERO HEADER
# ============================================================
st.markdown(
    f"""
    <div class="hero">
        <h1>🤖 TARUMT Smart Assistant</h1>
        <p>{lang['hero_desc']}</p>
        <span class="role-badge">{lang['connected']}: {current_name} — {user_role}</span>
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
#  BI ANALYTICS DASHBOARD
# ============================================================
nb_anomalies = 0
if MODULES_AVAILABLE and kpi_analyzer is not None and can_view_bi:
    total_sales = kpi_analyzer.total_sales()
    total_profit = kpi_analyzer.total_profit()

    report = anomaly_detector.get_anomaly_report()
    high_sales_neg_profit = report.get("high_sales_negative_profit_count", 0)
    high_disc_neg_profit = report.get("high_discount_negative_profit_count", 0)
    nb_anomalies = high_sales_neg_profit + high_disc_neg_profit

    anomaly_bg = "#fef3c7" if nb_anomalies > 0 else "#d1fae5"
    anomaly_fg = "#d97706" if nb_anomalies > 0 else "#059669"
    anomaly_sub = lang["anomaly_warn"] if nb_anomalies > 0 else lang["anomaly_ok"]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(kpi_card("💰", "Total Sales", f"${total_sales:,.0f}",
                             "#e0e7ff", "#4f46e5", lang["sales_sub"]),
                    unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("📈", "Total Profit", f"${total_profit:,.0f}",
                             "#dcfce7", "#16a34a", lang["profit_sub"]),
                    unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("🚨", "Anomalies", f"{nb_anomalies}",
                             anomaly_bg, anomaly_fg, anomaly_sub),
                    unsafe_allow_html=True)

    if nb_anomalies > 0:
        with st.expander(lang["anomaly_expander"]):
            st.write(f"- {lang['anomaly_sales']}: {high_sales_neg_profit}")
            st.write(f"- {lang['anomaly_disc']}: {high_disc_neg_profit}")

    st.write("")

elif MODULES_AVAILABLE and not can_view_bi:
    st.info(lang["bi_restricted_info"])


# ============================================================
#  Helper : rendu d'un message assistant (+ détail SQL)
# ============================================================
def render_assistant_message(message: dict):
    st.markdown(message["content"])
    if message.get("sql"):
        with st.expander(lang["sql_expander"]):
            st.code(message["sql"], language="sql")
            result = message.get("result")
            if result is not None and not result.empty:
                st.dataframe(result, use_container_width=True)


# ============================================================
#  CHAT
# ============================================================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": lang["welcome"]}
    ]

# Ajuste dynamiquement la langue du premier message d'accueil si l'historique contient uniquement ce message
if len(st.session_state.messages) == 1 and st.session_state.messages[0]["role"] == "assistant":
    st.session_state.messages[0]["content"] = lang["welcome"]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            render_assistant_message(message)
        else:
            st.markdown(message["content"])

if user_query := st.chat_input(lang["chat_placeholder"]):
    with st.chat_message("user"):
        st.markdown(user_query)
    st.session_state.messages.append({"role": "user", "content": user_query})

    # --- SÉCURITÉ MODULAIRE : Interception Prompt Injection OU Usurpation d'identité ---
    if detect_prompt_injection(user_query) or detect_cross_user_violation(user_query, current_name, user_role):
        should_ban = handle_security_violation(current_user, user_role, user_query)
        
        with st.chat_message("assistant"):
            if should_ban:
                st.error("🚨 CRITICAL WARNING: Security threshold exceeded. Your session has been terminated due to suspicious activities.")
                st.session_state["authenticated"] = False
                st.stop()
            else:
                alert_msg = f"⚠️ Security Alert: Unauthorized data access pattern detected. Action rejected. (Warning {st.session_state['security_violations']}/3)"
                st.warning(alert_msg)
                st.session_state.messages.append({"role": "assistant", "content": alert_msg})
                
    else:
        log_security_event(current_user, user_role, "ask_chatbot", "ALLOWED", f"Query: {user_query}")

        with st.chat_message("assistant"):
            with st.spinner(lang["spinner"]):
                assistant_message = {"role": "assistant", "content": "", "sql": None, "result": None}

                if not MODULES_AVAILABLE or engine is None:
                    assistant_message["content"] = "The chatbot core engine is currently unavailable."

                elif sql_agent is not None and user_role != "user":
                    try:
                        # Demander explicitement à l'agent de générer l'analyse dans la langue sélectionnée
                        localized_query = user_query + f" (Reply strictly in {selected_lang})"
                        outcome = sql_agent.ask(user_query, role=user_role)
                        
                        if outcome["error"]:
                            assistant_message["content"] = outcome["error"]
                            assistant_message["sql"] = outcome["sql"]
                            log_security_event(current_user, user_role, "sql_query", "REJECTED", f"Reason: {outcome['error']}")
                            
                            should_ban = check_sql_outcome_security(outcome["error"], current_user, user_role, user_query)
                        else:
                            answer = sql_agent.explain_result(localized_query, outcome["result"])
                            assistant_message["content"] = answer
                            assistant_message["sql"] = outcome["sql"]
                            assistant_message["result"] = outcome["result"]
                            log_security_event(current_user, user_role, "sql_query", "EXECUTED", f"SQL: {outcome['sql']}")
                    except Exception as e:
                        assistant_message["content"] = f"An error occurred: {str(e)}"

                else:
                    try:
                        assistant_message["content"] = engine.answer(user_query)
                        log_security_event(current_user, user_role, "local_engine_query", "EXECUTED", f"Query processed by secured fallback engine")
                    except Exception as e:
                        assistant_message["content"] = f"An error occurred during calculation: {str(e)}"

            if st.session_state.get("security_violations", 0) >= 3:
                st.error("🚨 CRITICAL WARNING: Security threshold exceeded. Your session has been terminated due to suspicious activities.")
                st.session_state["authenticated"] = False
                st.stop()
            else:
                render_assistant_message(assistant_message)
                st.session_state.messages.append(assistant_message)
            
            if st.session_state.get("security_violations", 0) >= 3:
                st.rerun()