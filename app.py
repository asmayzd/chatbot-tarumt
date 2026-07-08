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
        # Securely inject the key into the environment variables dynamically
        os.environ["GEMINI_API_KEY"] = config["API_KEYS"]["GEMINI_API_KEY"]

# Add root directory to path for imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# --- SÉCURITÉ : Importations des modules de contrôle ---
from src.security.auth import render_login_form
from src.security.logger import log_security_event

# Page Configuration (Placé impérativement avant toute exécution de composant de rendu Streamlit)
st.set_page_config(
    page_title="TARUMT Chatbot & BI Dashboard",
    page_icon="🤖",
    layout="wide"
)

# --- SÉCURITÉ : Vérification de la Session d'Authentification (RBAC) ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    render_login_form()
    st.stop()  # Interrompt immédiatement l'application tant que l'utilisateur n'est pas authentifié

# Récupération sécurisée de l'identité et du rôle de l'utilisateur actif
current_user = st.session_state["username"]
user_role = st.session_state["role"]

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
# Gemini will seamlessly detect the key initialized from your config.ini file
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

    # L'agent SQL interroge la base relationnelle persistante (schema.sql).
    sql_agent = None
    if USE_GEMINI_AI:
        sql_agent = SQLAgent(db_path="data/superstore_bi.db").setup()

    return engine, kpi, anomaly, sql_agent, df_clean

if MODULES_AVAILABLE:
    engine, kpi_analyzer, anomaly_detector, sql_agent, df_clean = init_components()
else:
    st.error(f"Failed to import project modules: {IMPORT_ERROR}")

# --- SIDEBAR: BI Analytics Dashboard ---
with st.sidebar:
    st.title("📊 BI & Analytics Panel")
    st.markdown(f"Connected as: **{current_user}** (`{user_role}`)") # Affichage du profil connecté
    st.markdown("Automated insights powered by `src/bi_analytics`.")
    st.write("---")

    if MODULES_AVAILABLE and kpi_analyzer is not None:
        st.subheader("📈 Key Performance Indicators")

        total_sales = kpi_analyzer.total_sales()
        total_profit = kpi_analyzer.total_profit()

        st.metric(label="Total Sales", value=f"${total_sales:,.2f}")
        st.metric(label="Total Profit", value=f"${total_profit:,.2f}")

        st.write("---")
        st.subheader("🚨 Anomaly Alerts")

        report = anomaly_detector.get_anomaly_report()
        high_sales_neg_profit = report.get("high_sales_negative_profit_count", 0)
        high_disc_neg_profit = report.get("high_discount_negative_profit_count", 0)
        nb_anomalies = high_sales_neg_profit + high_disc_neg_profit

        if nb_anomalies > 0:
            st.warning(f"{nb_anomalies} financial anomalies detected.")
            with st.expander("See details"):
                st.write(f"- High Sales with Negative Profit: {high_sales_neg_profit}")
                st.write(f"- High Discount with Negative Profit: {high_disc_neg_profit}")
        else:
            st.success("No critical financial anomalies found.")

        st.write("---")
        st.caption(f"🤖 SQL Agent: {'🟢 Active (Gemini)' if sql_agent else '🔴 Inactive'}")
    else:
        st.info("BI features will load once modules are fixed.")

    # Bouton de clôture de session (Log out)
    if st.button("🚪 Log out"):
        log_security_event(current_user, user_role, "logout", "SUCCESS", "Voluntary disconnection")
        st.session_state["authenticated"] = False
        st.rerun()


# --- Helper: render an assistant message (with optional SQL detail) ---
def render_assistant_message(message: dict):
    st.markdown(message["content"])

    # If this answer was produced by the SQL agent, show the query on demand.
    if message.get("sql"):
        with st.expander("🔍 Détails — requête SQL utilisée"):
            st.code(message["sql"], language="sql")

            result = message.get("result")
            if result is not None and not result.empty:
                st.dataframe(result, use_container_width=True)


# --- MAIN ZONE: Chatbot Interface ---
st.title("🤖 TARUMT Smart Assistant")
st.caption("Ask anything about sales, profits, shipping delays, or request deep business intelligence reasoning.")

# Handle Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I am your TARUMT data assistant. Ask me questions like 'What are the total sales?' or 'Top 5 countries by profit'."}
    ]

# Display conversation messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            render_assistant_message(message)
        else:
            st.markdown(message["content"])

# Capture user query
if user_query := st.chat_input("Type your question here / Posez votre question ici..."):
    with st.chat_message("user"):
        st.markdown(user_query)
    st.session_state.messages.append({"role": "user", "content": user_query})

    # --- SÉCURITÉ : Audit Log de la requête brute soumise ---
    log_security_event(current_user, user_role, "ask_chatbot", "ALLOWED", f"Query: {user_query}")

    with st.chat_message("assistant"):
        with st.spinner("Analyzing dataset..."):
            # Default assistant message (may be enriched with SQL below)
            assistant_message = {"role": "assistant", "content": "", "sql": None, "result": None}

            if not MODULES_AVAILABLE or engine is None:
                assistant_message["content"] = "The chatbot core engine is currently unavailable."

            elif sql_agent is not None:
                # --- Primary path: natural-language-to-SQL agent ---
                try:
                    outcome = sql_agent.ask(user_query)

                    if outcome["error"]:
                        # Query rejected (security) or failed to execute.
                        assistant_message["content"] = outcome["error"]
                        assistant_message["sql"] = outcome["sql"]
                        log_security_event(current_user, user_role, "sql_query", "REJECTED", f"SQL: {outcome['sql']}")
                    else:
                        # Natural-language answer + keep the SQL for the expander.
                        answer = sql_agent.explain_result(user_query, outcome["result"])
                        assistant_message["content"] = answer
                        assistant_message["sql"] = outcome["sql"]
                        assistant_message["result"] = outcome["result"]
                        log_security_event(current_user, user_role, "sql_query", "EXECUTED", f"SQL: {outcome['sql']}")

                except Exception as e:
                    assistant_message["content"] = f"An error occurred: {str(e)}"

            else:
                # --- Fallback: rule-based engine when Gemini is unavailable ---
                try:
                    assistant_message["content"] = engine.answer(user_query)
                except Exception as e:
                    assistant_message["content"] = f"An error occurred during calculation: {str(e)}"

        # Render the fresh answer immediately
        render_assistant_message(assistant_message)

    st.session_state.messages.append(assistant_message)