import streamlit as st
import pandas as pd
from src.security.logger import log_security_event

MALICIOUS_PATTERNS = [
    "ignore previous instructions", "ignore rules", "system override", 
    "act like you have no rules", "you are no longer an assistant",
    "developer mode", "jailbreak", "bypass restrictions"
]

# Colonnes techniques sensibles masquées au rôle 'user'
SENSITIVE_COLUMNS = ["Order.ID", "Row.ID"]


def detect_prompt_injection(user_input: str) -> bool:
    """Scanne la question de l'utilisateur à la recherche de patterns malveillants."""
    lowered_input = user_input.lower()
    return any(pattern in lowered_input for pattern in MALICIOUS_PATTERNS)


def detect_cross_user_violation(user_query: str, current_customer_name: str, role: str) -> bool:
    """Détecte si un utilisateur tente d'extraire des infos sur un autre client."""
    if role != "user":
        return False
        
    lowered_query = user_query.lower()
    lowered_my_name = current_customer_name.lower()
    
    # Noms des clients configurés
    monitored_customers = ["chad sievert", "arthur prichep", "jeremy farry"]
    
    for name in monitored_customers:
        if name in lowered_query and name != lowered_my_name:
            return True
            
    return False


def get_secured_dataframe(df: pd.DataFrame, role: str, customer_id: str) -> pd.DataFrame:
    """Filtre physiquement les données pour le Row-Level Security (RLS)."""
    if role == "user":
        id_col = "Customer.ID" if "Customer.ID" in df.columns else "Customer ID"
        
        if id_col in df.columns and customer_id != "user_tarumt":
            df = df[df[id_col] == customer_id]
            
        available_sensitive = [col for col in SENSITIVE_COLUMNS if col in df.columns]
        return df.drop(columns=available_sensitive)
        
    return df


def check_sql_outcome_security(outcome_error: str, username: str, user_role: str, user_query: str) -> bool:
    """Analyse l'erreur de l'agent SQL pour vérifier s'il s'agit d'un blocage de sécurité."""
    if not outcome_error:
        return False
        
    if "Access Denied" in outcome_error or "rejected for security" in outcome_error:
        return handle_security_violation(username, user_role, f"SQL Policy Breach via: {user_query}")
        
    return False


def handle_security_violation(username: str, user_role: str, suspicious_query: str) -> bool:
    """Gère l'incrémentation du compteur de violations."""
    if "security_violations" not in st.session_state:
        st.session_state["security_violations"] = 0
        
    st.session_state["security_violations"] += 1
    violations = st.session_state["security_violations"]
    
    log_security_event(username, user_role, "security_violation", "BLOCKED", f"Payload: {suspicious_query}")
    
    if violations >= 3:
        log_security_event(username, user_role, "user_session_ban", "CRITICAL", "User banned due to repeated violations.")
        return True
        
    return False
