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

# Page Configuration
st.set_page_config(
    page_title="TARUMT Chatbot & BI Dashboard",
    page_icon="🤖",
    layout="wide"
)

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
user_role = st.session_state["role"]

# Rôles autorisés à voir le tableau de bord BI Analytics
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
        return None, None, None, None, None

    loader = DataLoader(file_path="data/superstore.csv")
    df = loader.load_csv()
    cleaner = DataCleaner(df)
    df_clean = cleaner.clean()

    engine = ChatbotEngine(df_clean)
    kpi = KPIAnalyzer(df_clean)
    anomaly = AnomalyDetector(df_clean)

    sql_agent = None
    if USE_GEMINI_AI:
        sql_agent = SQLAgent(db_path="data/superstore_bi.db").setup()

    return engine, kpi, anomaly, sql_agent, df_clean

if MODULES_AVAILABLE:
    engine, kpi_analyzer, anomaly_detector, sql_agent, df_clean = init_components()
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
    st.markdown(
        f'<div class="profile-card">'
        f'<div class="profile-name">👤 {current_user}</div>'
        f'<div class="profile-role">{user_role}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    st.caption(f"🤖 SQL Agent: {'🟢 Active (Gemini)' if (MODULES_AVAILABLE and sql_agent) else '🔴 Inactive'}")

    if can_view_bi:
        st.caption("📊 BI Analytics: 🟢 Accès autorisé")
    else:
        st.caption("📊 BI Analytics: 🔒 Réservé (analyst / admin)")

    st.write("---")

    if st.button("🚪 Log out", use_container_width=True):
        log_security_event(current_user, user_role, "logout", "SUCCESS", "Voluntary disconnection")
        st.session_state["authenticated"] = False
        st.rerun()


# ============================================================
#  HERO HEADER
# ============================================================
st.markdown(
    f"""
    <div class="hero">
        <h1>🤖 TARUMT Smart Assistant</h1>
        <p>Posez vos questions sur les ventes, profits et délais de livraison en langage naturel.</p>
        <span class="role-badge">Connecté : {current_user} — {user_role}</span>
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
#  BI ANALYTICS DASHBOARD — réservé analyst / admin
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
    anomaly_sub = "à surveiller" if nb_anomalies > 0 else "aucune alerte critique"

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(kpi_card("💰", "Total Sales", f"${total_sales:,.0f}",
                             "#e0e7ff", "#4f46e5", "chiffre d'affaires global"),
                    unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("📈", "Total Profit", f"${total_profit:,.0f}",
                             "#dcfce7", "#16a34a", "bénéfice net global"),
                    unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("🚨", "Anomalies", f"{nb_anomalies}",
                             anomaly_bg, anomaly_fg, anomaly_sub),
                    unsafe_allow_html=True)

    if nb_anomalies > 0:
        with st.expander("Voir le détail des anomalies financières"):
            st.write(f"- Ventes élevées avec profit négatif : {high_sales_neg_profit}")
            st.write(f"- Remises élevées avec profit négatif : {high_disc_neg_profit}")

    st.write("")

elif MODULES_AVAILABLE and not can_view_bi:
    st.info("🔒 Le tableau de bord BI Analytics est réservé aux rôles **analyst** et **admin**. "
            "Vous pouvez néanmoins poser vos questions à l'assistant ci-dessous.")


# ============================================================
#  Helper : rendu d'un message assistant (+ détail SQL)
# ============================================================
def render_assistant_message(message: dict):
    st.markdown(message["content"])
    if message.get("sql"):
        with st.expander("🔍 Détails — requête SQL utilisée"):
            st.code(message["sql"], language="sql")
            result = message.get("result")
            if result is not None and not result.empty:
                st.dataframe(result, use_container_width=True)


# ============================================================
#  CHAT
# ============================================================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Bonjour ! Je suis votre assistant data TARUMT. "
                                          "Essayez par exemple : « Top 5 des pays par ventes » ou « profit par catégorie »."}
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            render_assistant_message(message)
        else:
            st.markdown(message["content"])

if user_query := st.chat_input("Posez votre question ici / Type your question here..."):
    with st.chat_message("user"):
        st.markdown(user_query)
    st.session_state.messages.append({"role": "user", "content": user_query})

    log_security_event(current_user, user_role, "ask_chatbot", "ALLOWED", f"Query: {user_query}")

    with st.chat_message("assistant"):
        with st.spinner("Analyse en cours..."):
            assistant_message = {"role": "assistant", "content": "", "sql": None, "result": None}

            if not MODULES_AVAILABLE or engine is None:
                assistant_message["content"] = "The chatbot core engine is currently unavailable."

            elif sql_agent is not None:
                try:
                    outcome = sql_agent.ask(user_query)
                    if outcome["error"]:
                        assistant_message["content"] = outcome["error"]
                        assistant_message["sql"] = outcome["sql"]
                        log_security_event(current_user, user_role, "sql_query", "REJECTED", f"SQL: {outcome['sql']}")
                    else:
                        answer = sql_agent.explain_result(user_query, outcome["result"])
                        assistant_message["content"] = answer
                        assistant_message["sql"] = outcome["sql"]
                        assistant_message["result"] = outcome["result"]
                        log_security_event(current_user, user_role, "sql_query", "EXECUTED", f"SQL: {outcome['sql']}")
                except Exception as e:
                    assistant_message["content"] = f"An error occurred: {str(e)}"

            else:
                try:
                    assistant_message["content"] = engine.answer(user_query)
                except Exception as e:
                    assistant_message["content"] = f"An error occurred during calculation: {str(e)}"

        render_assistant_message(assistant_message)

    st.session_state.messages.append(assistant_message)