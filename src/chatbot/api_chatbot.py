"""
Module Data Science / ML — API du chatbot (FastAPI).

Expose le pipeline complet en HTTP :
    POST /login  { "username", "password" }        -> token
    POST /chat   { "question" }  + header Authorization: Bearer <token>

Le flux /chat applique : sécurité -> chatbot -> logs (comme dans l'app Streamlit).

Lancer :  uvicorn src.chatbot.api_chatbot:app --reload
Docs interactives :  http://127.0.0.1:8000/docs
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from src.security import auth, security_rules, logs
from src.chatbot.chatbot_engine import chatbot_response

app = FastAPI(title="Chatbot E-commerce sécurisé",
              description="API du chatbot d'analyse de données e-commerce.",
              version="1.0")


class LoginInput(BaseModel):
    username: str
    password: str


class ChatInput(BaseModel):
    question: str


@app.get("/")
def racine():
    return {"message": "API Chatbot E-commerce. Voir /docs pour tester."}


@app.post("/login")
def login(data: LoginInput):
    res = auth.authenticate(data.username, data.password)
    if not res["success"]:
        raise HTTPException(status_code=401, detail=res["reason"])
    return {"token": res["token"], "role": res["role"]}


def _session_depuis_header(authorization: str):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Token manquant.")
    token = authorization.split(" ", 1)[1]
    sess = auth.verify_token(token)
    if not sess:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré.")
    return sess


@app.post("/chat")
def chat(data: ChatInput, authorization: str = Header(default="")):
    sess = _session_depuis_header(authorization)
    role, user = sess["role"], sess["username"]

    # 1) Sécurité
    secu = security_rules.check_security(data.question, role)
    if not secu["allowed"]:
        logs.log_interaction(user, role, data.question, False,
                             secu["risk_level"], secu["category"],
                             "Requête bloquée : " + secu["reason"])
        return {"answer": "⛔ " + secu["reason"], "allowed": False,
                "risk_level": secu["risk_level"], "category": secu["category"],
                "source": None}

    # 2) Chatbot
    rep = chatbot_response(data.question, role)

    # 3) Logs
    logs.log_interaction(user, role, data.question, True,
                         secu["risk_level"], rep["category"], rep["answer"])

    return {"answer": rep["answer"], "allowed": True,
            "risk_level": secu["risk_level"], "category": rep["category"],
            "intent": rep["intent"], "source": rep["source"],
            "confidence": rep["confidence"]}


@app.get("/logs")
def get_logs(authorization: str = Header(default="")):
    sess = _session_depuis_header(authorization)
    if not auth.can_access(sess["role"], "logs"):
        raise HTTPException(status_code=403, detail="Accès aux logs réservé à l'admin.")
    return logs.read_logs().to_dict(orient="records")
