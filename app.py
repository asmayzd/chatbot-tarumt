import streamlit as st
import pandas as pd
import sys
import os

# Ajouter le dossier racine au path pour les imports relatifs
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Importations des modules du projet
try:
    from src.data_science.chatbot_engine import ChatbotEngine
    from src.bi_analytics.kpi_analyzer import KPIAnalyzer
    from src.bi_analytics.anomaly_detector import AnomalyDetector
    from src.data_science.data_loader import DataLoader
    from src.data_science.data_cleaner import DataCleaner
    MODULES_AVAILABLE = True
except ImportError as e:
    MODULES_AVAILABLE = False
    IMPORT_ERROR = str(e)

# Configuration de la page
st.set_page_config(
    page_title="TARUMT Chatbot & BI Dashboard",
    page_icon="🤖",
    layout="wide"
)

# --- Initialisation des composants en cache ---
@st.cache_resource
def init_components():
    if not MODULES_AVAILABLE:
        return None, None, None, None
    
    # Correction précédente : Chargement via load_csv()
    loader = DataLoader(file_path="data/superstore.csv")
    df = loader.load_csv()
    
    # Correction actuelle : Appel de la méthode .clean() à la place de .clean_data()
    cleaner = DataCleaner(df)
    df_clean = cleaner.clean() 
    
    # Initialisation du chatbot et des outils BI (avec injection du DataFrame nettoyé)
    engine = ChatbotEngine(df_clean)
    kpi = KPIAnalyzer(df_clean)
    anomaly = AnomalyDetector(df_clean)
    
    return engine, kpi, anomaly, df_clean

if MODULES_AVAILABLE:
    engine, kpi_analyzer, anomaly_detector, df_clean = init_components()
else:
    st.error(f"Erreur d'importation des modules du projet : {IMPORT_ERROR}")

# --- BARRE LATÉRALE : Tableau de bord BI ---
with st.sidebar:
    st.title("📊 BI & Analytics Panel")
    st.markdown("Vue d'ensemble automatisée basée sur vos modules `src/bi_analytics`.")
    st.write("---")
    
    if MODULES_AVAILABLE and kpi_analyzer is not None:
        st.subheader("📈 Indicateurs Clés (KPIs)")
        
        # Utilisation des méthodes de KPIAnalyzer (qui pointent vers 'sales' et 'profit' en minuscules)
        total_sales = kpi_analyzer.total_sales()
        total_profit = kpi_analyzer.total_profit()
        
        st.metric(label="Ventes Totales", value=f"${total_sales:,.2f}")
        st.metric(label="Profit Total", value=f"${total_profit:,.2f}")
        
        st.write("---")
        st.subheader("🚨 Alertes Anomalies")
        
        # Génération du rapport via AnomalyDetector
        report = anomaly_detector.get_anomaly_report()
        nb_anomalies = (
            report.get("high_sales_negative_profit_count", 0) + 
            report.get("high_discount_negative_profit_count", 0)
        )
        
        if nb_anomalies > 0:
            st.warning(f"{nb_anomalies} transactions anormales (pertes financières) détectées.")
        else:
            st.success("Aucune anomalie financière critique détectée.")
    else:
        st.info("Les fonctionnalités BI s'activeront lorsque les modules seront fonctionnels.")

# --- ZONE PRINCIPALE : L'interface Chatbot ---
st.title("🤖 Assistant Intelligent TARUMT")
st.caption("Posez vos questions en anglais ou français sur les indicateurs de ventes, les performances ou les pays.")

# Gestion de l'historique des discussions (session_state)
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Bonjour ! Je suis l'assistant TARUMT. Posez-moi une question sur les ventes (sales), le profit ou les délais !"}
    ]

# Affichage des messages de la conversation
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Capture de la saisie utilisateur
if user_query := st.chat_input("Ex: What are the total sales? / Quel est le profit total ?"):
    # Affichage du message utilisateur
    with st.chat_message("user"):
        st.markdown(user_query)
    st.session_state.messages.append({"role": "user", "content": user_query})
    
    # Génération de la réponse via le ChatbotEngine du projet
    with st.chat_message("assistant"):
        with st.spinner("Analyse des données en cours..."):
            if MODULES_AVAILABLE and engine is not None:
                try:
                    # Correction : Appel de la méthode answer() définie dans votre ChatbotEngine
                    response = engine.answer(user_query)
                except Exception as e:
                    response = f"Une erreur est survenue lors de l'analyse : {str(e)}"
            else:
                response = "Le moteur du chatbot n'est pas disponible. Veuillez vérifier vos dépendances."
        
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})