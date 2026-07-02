# Architecture

## Vue d'ensemble

Le système est une application modulaire en 3 couches, orchestrées par
`src/app.py` (Streamlit) ou `src/chatbot/api_chatbot.py` (FastAPI).

```
                    ┌─────────────────────────────┐
                    │      Interface (app.py)      │
                    │   login · chat · dashboard   │
                    └──────────────┬──────────────┘
                                   │
        ┌──────────────┬───────────┴───────────┬──────────────┐
        ▼              ▼                       ▼              ▼
   ┌─────────┐   ┌───────────┐          ┌───────────┐   ┌─────────┐
   │ SÉCURITÉ│   │  CHATBOT  │          │    BI     │   │  LOGS   │
   │ auth    │   │  engine   │          │ kpi_calc  │   │ logs.py │
   │ rules   │   │  rag      │          │ dashboard │   │         │
   └─────────┘   └─────┬─────┘          └─────┬─────┘   └─────────┘
                       │                       │
                       └──────────┬────────────┘
                                  ▼
                     ┌──────────────────────────┐
                     │  data/processed/*.csv     │
                     │  data/documents/*.md      │
                     └──────────────────────────┘
```

## Contrats entre modules

Les modules communiquent uniquement via des fonctions au format normalisé,
ce qui permet de développer chaque partie en parallèle et de remplacer une
implémentation sans casser les autres.

```python
# Sécurité (module cyber)
check_security(question: str, role: str) -> {
    "allowed": bool, "reason": str, "risk_level": str, "category": str }

# Chatbot (module ML)
chatbot_response(question: str, role: str) -> {
    "answer": str, "source": str, "confidence": float,
    "category": str, "intent": str }

# BI (module analytics)
get_kpi(metric_name: str) -> {
    "metric": str, "value": ..., "detail": ..., "period": str, "unit": str }
```

## Flux d'une requête

1. L'utilisateur se connecte → `auth.authenticate` renvoie un token + rôle.
2. Il pose une question → `check_security(question, role)`.
   - Si bloquée : la requête est journalisée et une réponse de refus est renvoyée.
3. Sinon → `chatbot_response(question, role)` :
   - `detecter_intention` classe la question (kpi / tendance / anomalie /
     documentaire / général).
   - Routage vers `get_kpi(...)` (données) ou `rag_pipeline.answer_from_docs(...)`.
4. La réponse est journalisée via `log_interaction(...)`.
5. Le dashboard lit les logs et le dataset pour ses analytics.

## Choix techniques

| Besoin | Choix | Alternative possible |
|--------|-------|----------------------|
| Détection d'intention | règles + mots-clés FR | modèle NLP / LLM |
| Recherche documentaire | TF-IDF + cosinus (scikit-learn) | FAISS, ChromaDB, embeddings |
| Stockage données | CSV | base SQL (PostgreSQL, SQLite) |
| Auth | SHA-256 + sel + token | OAuth2 / JWT + bcrypt |
| Dashboard | Streamlit + Plotly | Power BI, Tableau |
| API | FastAPI | Flask |

## Extension vers un vrai LLM / RAG

Le prompt système est déjà défini dans `prompts.PROMPT_SYSTEME`. Pour brancher
un LLM, il suffit de remplacer le corps de `chatbot_response` : conserver la
détection d'intention et le RAG pour construire le contexte, puis appeler le
LLM avec `PROMPT_SYSTEME.format(contexte=..., role=..., question=...)`. Le
contrat de sortie reste identique, donc `app.py` et l'API n'ont pas à changer.
