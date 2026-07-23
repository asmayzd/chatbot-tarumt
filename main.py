"""
FastAPI backend for the TARUMT Smart Assistant.

This exposes the existing project logic (SQL agent, KPIs, guardrails, auth)
as a JSON API that a Vue frontend can call. No business logic lives here:
this file only wires the existing `src/` modules to HTTP endpoints.

Run with:
    uvicorn main:app --reload
Interactive docs once running:
    http://127.0.0.1:8000/docs
"""

import os
import uuid
import configparser
import pandas as pd

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- Load the Gemini key exactly like the Streamlit app did ---
config = configparser.ConfigParser()
if os.path.exists("config.ini"):
    config.read("config.ini")
    if "API_KEYS" in config and "GEMINI_API_KEY" in config["API_KEYS"]:
        os.environ["GEMINI_API_KEY"] = config["API_KEYS"]["GEMINI_API_KEY"]

# --- Existing project logic (unchanged, imported where it already lives) ---
from src.database.db_manager import init_db, get_db_connection
from src.security.auth import verify_credentials
from src.security.logger import log_security_event
from src.security.guardrails import detect_prompt_injection, detect_cross_user_violation
from src.data_science.data_cleaner import DataCleaner
from src.bi_analytics.kpi_analyzer import KPIAnalyzer
from src.bi_analytics.anomaly_detector import AnomalyDetector
from src.bi_analytics.sql_agent import SQLAgent


# ==========================================================================
#  App setup
# ==========================================================================
app = FastAPI(title="TARUMT Smart Assistant API", version="1.0")

# Allow the Vue dev server (default Vite port) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BI_ALLOWED_ROLES = ("admin", "analyst")

# Suggested questions per role (mirrors the Streamlit version).
SUGGESTIONS = {
    "user": [
        "How many orders have I placed?",
        "What is my total spending?",
        "Which region did I order from most?",
    ],
    "analyst": [
        "Top 5 countries by sales",
        "Profit by category",
        "Which products lose the most money?",
        "Average shipping delay by region",
    ],
    "admin": [
        "Top 5 countries by sales",
        "Profit by category",
        "Which products lose the most money?",
        "How many customers per segment?",
    ],
}


# ==========================================================================
#  In-memory session store
# ==========================================================================
SESSIONS = {}          # token -> {"username", "role", "customer_name", "violations"}


def get_session(token: str) -> dict:
    """Resolve a bearer token to its session, or raise 401."""
    session = SESSIONS.get(token)
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    return session


# ==========================================================================
#  Heavy singletons: loaded once at startup, shared across requests
# ==========================================================================
KPI = None
ANOMALY = None
AGENT = None


@app.on_event("startup")
def load_components():
    """Load data and models once when the server starts directly from PostgreSQL."""
    global KPI, ANOMALY, AGENT

    init_db()

    # --- Connexion à PostgreSQL & Récupération dynamique des données ---
    conn = get_db_connection()
    try:
        query = """
            SELECT 
                o.order_id, o.order_date, o.ship_date, o.ship_mode, o.customer_id,
                c.customer_name, c.segment,
                oi.sales, oi.quantity, oi.discount, oi.profit,
                p.product_id, p.product_name, p.category, p.sub_category
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN products p ON oi.product_id = p.product_id;
        """
        df = pd.read_sql(query, conn)
    finally:
        conn.close()

    df_clean = DataCleaner(df).clean()

    KPI = KPIAnalyzer(df_clean)
    ANOMALY = AnomalyDetector(df_clean)

    # --- Configuration du SQLAgent (sur son fichier DB SQLite) ---
    if "GEMINI_API_KEY" in os.environ:
        AGENT = SQLAgent(db_path="data/superstore_bi.db").setup()


# ==========================================================================
#  Request / response models
# ==========================================================================
class LoginRequest(BaseModel):
    username: str
    password: str


class AskRequest(BaseModel):
    question: str


# ==========================================================================
#  Endpoints
# ==========================================================================
@app.post("/login")
def login(body: LoginRequest):
    """Authenticate and return a session token."""
    role, customer_name = verify_credentials(body.username, body.password)

    if not role:
        log_security_event(body.username, "UNKNOWN", "login", "FAILED", "Bad credentials")
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = uuid.uuid4().hex
    SESSIONS[token] = {
        "username": body.username,
        "role": role,
        "customer_name": customer_name,
        "violations": 0,
    }
    log_security_event(body.username, role, "login", "SUCCESS", "API login")

    return {
        "token": token,
        "username": body.username,
        "customer_name": customer_name,
        "role": role,
        "can_view_bi": role in BI_ALLOWED_ROLES,
    }


@app.post("/logout")
def logout(authorization: str = Header(None)):
    """Invalidate the session token."""
    token = (authorization or "").replace("Bearer ", "")
    session = SESSIONS.pop(token, None)
    if session:
        log_security_event(session["username"], session["role"], "logout", "SUCCESS", "API logout")
    return {"ok": True}


@app.get("/me")
def me(authorization: str = Header(None)):
    """Return the current user's profile (used by the frontend on load)."""
    token = (authorization or "").replace("Bearer ", "")
    session = get_session(token)
    return {
        "username": session["username"],
        "customer_name": session["customer_name"],
        "role": session["role"],
        "can_view_bi": session["role"] in BI_ALLOWED_ROLES,
    }


@app.get("/suggestions")
def suggestions(authorization: str = Header(None)):
    """Role-appropriate suggested questions."""
    token = (authorization or "").replace("Bearer ", "")
    session = get_session(token)
    return {"suggestions": SUGGESTIONS.get(session["role"], [])}


@app.get("/kpis")
def kpis(authorization: str = Header(None)):
    """BI dashboard figures. Restricted to analyst / admin."""
    token = (authorization or "").replace("Bearer ", "")
    session = get_session(token)

    if session["role"] not in BI_ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="BI dashboard reserved for analyst / admin.")

    report = ANOMALY.get_anomaly_report()
    nb_anomalies = (
        report.get("high_sales_negative_profit_count", 0)
        + report.get("high_discount_negative_profit_count", 0)
    )

    return {
        "total_sales": float(KPI.total_sales()),
        "total_profit": float(KPI.total_profit()),
        "anomalies": int(nb_anomalies),
    }


@app.post("/ask")
def ask(body: AskRequest, authorization: str = Header(None)):
    """Main endpoint: natural-language question -> answer + SQL."""
    token = (authorization or "").replace("Bearer ", "")
    session = get_session(token)

    username = session["username"]
    role = session["role"]
    customer_name = session["customer_name"]
    question = body.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Empty question.")

    # --- Security guardrails (prompt injection / impersonation) ---
    if detect_prompt_injection(question) or detect_cross_user_violation(question, customer_name, role):
        session["violations"] += 1
        log_security_event(username, role, "security_violation", "BLOCKED", f"Payload: {question}")

        if session["violations"] >= 3:
            log_security_event(username, role, "user_session_ban", "CRITICAL", "Repeated violations")
            SESSIONS.pop(token, None)
            raise HTTPException(status_code=403, detail="Session terminated: security threshold exceeded.")

        return {
            "content": f"Security alert: request rejected. (Warning {session['violations']}/3)",
            "sql": None,
            "result": None,
            "blocked": True,
        }

    if AGENT is None:
        raise HTTPException(status_code=503, detail="SQL agent unavailable (no Gemini key).")

    log_security_event(username, role, "ask_chatbot", "ALLOWED", f"Query: {question}")

    # For a `user`, username == customer_id, used to scope the DB views.
    outcome = AGENT.ask(question, role=role, customer_id=username)

    if outcome["error"]:
        log_security_event(username, role, "sql_query", "REJECTED", f"Reason: {outcome['error']}")
        return {"content": outcome["error"], "sql": outcome["sql"], "result": None, "blocked": False}

    answer = AGENT.explain_result(question, outcome["result"])
    log_security_event(username, role, "sql_query", "EXECUTED", f"SQL: {outcome['sql']}")

    # Convert numpy dtypes to native Python types so FastAPI can serialise them.
    records = outcome["result"].astype(object).where(
        outcome["result"].notna(), None
    ).to_dict(orient="records")
    records = [
        {k: (v.item() if hasattr(v, "item") else v) for k, v in row.items()}
        for row in records
    ]

    return {
        "content": answer,
        "sql": outcome["sql"],
        "result": records,
        "cached": outcome.get("cached", False),
        "blocked": False,
    }


@app.get("/")
def root():
    return {"status": "ok", "service": "TARUMT Smart Assistant API"}