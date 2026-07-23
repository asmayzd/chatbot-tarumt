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
from src.database import chat_history
from src.security.auth import verify_credentials
from src.security.logger import log_security_event
from src.security.guardrails import detect_prompt_injection, detect_cross_user_violation
from src.security import ai_guardrails
from src.security import security_dashboard
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


def _ensure_session_owner(user_id: int, chat_session_id: int):
    """Raise 404 if chat_session_id doesn't belong to user_id (no cross-user reads)."""
    owned_ids = {s["session_id"] for s in chat_history.list_sessions(user_id)}
    if chat_session_id not in owned_ids:
        raise HTTPException(status_code=404, detail="Conversation not found.")


def _require_admin(token: str) -> dict:
    """Resolve the session for `token` and raise 403 unless it's an admin."""
    session = get_session(token)
    if session["role"] != "admin":
        raise HTTPException(status_code=403, detail="Reserved for the admin role.")
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

    # Provisionne les comptes admin/analyst et les comptes clients manquants
    # (idempotent : ne recrée jamais un compte déjà existant).
    from src.database.seed_users import seed_default_accounts
    seed_default_accounts()

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
    session_id: int | None = None


class CreateSessionRequest(BaseModel):
    session_name: str | None = None


class RenameSessionRequest(BaseModel):
    session_name: str


# ==========================================================================
#  Endpoints
# ==========================================================================
@app.post("/login")
def login(body: LoginRequest):
    """Authenticate and return a session token."""
    role, customer_name, user_id = verify_credentials(body.username, body.password)

    if not role:
        log_security_event(body.username, "UNKNOWN", "login", "FAILED", "Bad credentials")
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = uuid.uuid4().hex
    SESSIONS[token] = {
        "username": body.username,
        "role": role,
        "customer_name": customer_name,
        "user_id": user_id,
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


@app.get("/sessions")
def get_sessions(authorization: str = Header(None)):
    """List the current user's chat conversations, most recent first."""
    token = (authorization or "").replace("Bearer ", "")
    session = get_session(token)
    return {"sessions": chat_history.list_sessions(session["user_id"])}


@app.post("/sessions")
def create_chat_session(body: CreateSessionRequest, authorization: str = Header(None)):
    """Start a new, empty conversation for the current user."""
    token = (authorization or "").replace("Bearer ", "")
    session = get_session(token)
    name = body.session_name or chat_history.DEFAULT_SESSION_NAME
    session_id = chat_history.create_session(session["user_id"], name)
    return {"session_id": session_id, "session_name": name}


@app.get("/sessions/{chat_session_id}/messages")
def get_chat_session_messages(chat_session_id: int, authorization: str = Header(None)):
    """Load the full message history of one of the current user's conversations."""
    token = (authorization or "").replace("Bearer ", "")
    session = get_session(token)
    _ensure_session_owner(session["user_id"], chat_session_id)
    return {"messages": chat_history.load_messages(chat_session_id)}


@app.patch("/sessions/{chat_session_id}")
def rename_chat_session(chat_session_id: int, body: RenameSessionRequest, authorization: str = Header(None)):
    token = (authorization or "").replace("Bearer ", "")
    session = get_session(token)
    _ensure_session_owner(session["user_id"], chat_session_id)
    chat_history.rename_session(chat_session_id, body.session_name)
    return {"ok": True}


@app.delete("/sessions/{chat_session_id}")
def delete_chat_session(chat_session_id: int, authorization: str = Header(None)):
    token = (authorization or "").replace("Bearer ", "")
    session = get_session(token)
    _ensure_session_owner(session["user_id"], chat_session_id)
    chat_history.delete_session(chat_session_id)
    return {"ok": True}


@app.get("/admin/security/overview")
def admin_security_overview(authorization: str = Header(None)):
    """KPIs + série temporelle (14j) pour le dashboard cybersécurité. Admin only."""
    token = (authorization or "").replace("Bearer ", "")
    _require_admin(token)
    return security_dashboard.get_overview()


@app.get("/admin/security/events")
def admin_security_events(
    limit: int = 100,
    status: str | None = None,
    action: str | None = None,
    authorization: str = Header(None),
):
    """Derniers événements de sécurité (connexions, blocages, bannissements...). Admin only."""
    token = (authorization or "").replace("Bearer ", "")
    _require_admin(token)
    limit = max(1, min(limit, 500))
    status_list = status.split(",") if status else None
    action_list = action.split(",") if action else None
    return {"events": security_dashboard.get_events(limit=limit, status=status_list, action=action_list)}


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
    user_id = session["user_id"]
    question = body.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Empty question.")

    # --- Persistance : rattache la question à une conversation réelle. On en
    # crée une nouvelle si le frontend n'en a pas encore (première question).
    if body.session_id is not None:
        _ensure_session_owner(user_id, body.session_id)
        chat_session_id = body.session_id
    else:
        chat_session_id = chat_history.create_session(user_id)

    is_first_message = chat_history.count_messages(chat_session_id) == 0
    chat_history.append_message(chat_session_id, "user", question)
    if is_first_message:
        chat_history.rename_session(chat_session_id, question[:60])

    def respond(content, sql=None, result=None, blocked=False, extra=None):
        chat_history.append_message(chat_session_id, "assistant", content)
        payload = {
            "content": content,
            "sql": sql,
            "result": result,
            "blocked": blocked,
            "session_id": chat_session_id,
        }
        if extra:
            payload.update(extra)
        return payload

    # --- Security guardrails ---
    # Couche 1 : blacklist statique, instantanée, gratuite (patterns connus).
    # Couche 2 : uniquement si la couche 1 n'a rien vu, Gemini juge la requête —
    # utile contre les formulations inédites, sans avoir à enrichir la blacklist
    # à la main à chaque nouvelle attaque.
    blacklist_hit = detect_prompt_injection(question)
    cross_user_hit = detect_cross_user_violation(question, customer_name, role)

    ai_verdict = None
    if not (blacklist_hit or cross_user_hit):
        ai_verdict = ai_guardrails.classify_intent(question)

    is_malicious = blacklist_hit or cross_user_hit or bool(ai_verdict and ai_verdict["malicious"])

    if is_malicious:
        if blacklist_hit:
            category = "blacklist"
        elif cross_user_hit:
            category = "cross_user_violation"
        else:
            category = ai_verdict["category"]

        session["violations"] += 1
        log_security_event(
            username, role, "security_violation", "BLOCKED",
            f"[{category}] Payload: {question}"
            + (f" | AI reason: {ai_verdict['reason']}" if ai_verdict and ai_verdict["malicious"] else ""),
        )

        if session["violations"] >= 3:
            log_security_event(username, role, "user_session_ban", "CRITICAL", "Repeated violations")
            SESSIONS.pop(token, None)
            raise HTTPException(status_code=403, detail="Session terminated: security threshold exceeded.")

        return respond(
            f"Security alert: request rejected. (Warning {session['violations']}/3)",
            blocked=True,
        )

    if AGENT is None:
        raise HTTPException(status_code=503, detail="SQL agent unavailable (no Gemini key).")

    log_security_event(username, role, "ask_chatbot", "ALLOWED", f"Query: {question}")

    # For a `user`, username == customer_id, used to scope the DB views.
    outcome = AGENT.ask(question, role=role, customer_id=username)

    if outcome["error"]:
        log_security_event(username, role, "sql_query", "REJECTED", f"Reason: {outcome['error']}")
        return respond(outcome["error"], sql=outcome["sql"])

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

    return respond(
        answer, sql=outcome["sql"], result=records,
        extra={"cached": outcome.get("cached", False)},
    )


@app.get("/")
def root():
    return {"status": "ok", "service": "TARUMT Smart Assistant API"}