# Chatbot intelligent sécurisé — analyse de données e-commerce

Projet de recherche : un chatbot qui répond à des questions métier sur des
données e-commerce (KPI, tendances, anomalies, FAQ), avec une couche de
sécurité (authentification, rôles, filtre anti-injection, logs) et un
dashboard analytique.

Le projet est découpé en 3 modules qui suivent des **contrats** clairs, pour
travailler en parallèle sans se bloquer :

| Module | Rôle | Contrat exposé |
|--------|------|----------------|
| `src/analytics` | BI & Analytics | `get_kpi(metric_name) -> dict` |
| `src/chatbot`   | Data Science / ML | `chatbot_response(question, role) -> dict` |
| `src/security`  | Cybersécurité | `check_security(question, role) -> dict` |

## Pipeline

```
Question utilisateur
   ↓
Vérification sécurité   (check_security)
   ↓
Traitement IA           (chatbot_response → détection d'intention)
   ↓
Accès aux données/KPI   (get_kpi / RAG documentaire)
   ↓
Réponse chatbot
   ↓
Sauvegarde logs         (log_interaction)
   ↓
Dashboard analytics
```

## Installation

```bash
pip install -r requirements.txt
python data/generate_dataset.py        # génère le dataset (déjà inclus)
```

## Lancer l'application (démo complète)

```bash
streamlit run src/app.py
```

Comptes de démonstration :

| Utilisateur | Mot de passe   | Rôle        | Accès |
|-------------|----------------|-------------|-------|
| `admin`     | `admin123`     | admin       | KPI, données clients, logs |
| `besma`     | `analyste123`  | analyste    | KPI + dashboard |
| `invite`    | `invite123`    | utilisateur | accès limité |

## Lancer l'API (alternative)

```bash
uvicorn src.chatbot.api_chatbot:app --reload
# Docs interactives : http://127.0.0.1:8000/docs
```

Exemple :
```bash
# 1) login -> récupérer le token
curl -X POST http://127.0.0.1:8000/login -H "Content-Type: application/json" \
     -d '{"username":"besma","password":"analyste123"}'
# 2) poser une question
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" \
     -H "Authorization: Bearer <TOKEN>" \
     -d '{"question":"Quel est le chiffre d'\''affaires total ?"}'
```

## Tests

```bash
pytest tests/ -q                        # tests unitaires (23)
python src/chatbot/evaluate.py          # évaluation du chatbot -> evaluation_results.csv
python src/security/attack_tests.py     # tests d'attaques -> attack_tests.csv
```

## Structure

```
chatbot-research-project/
├── data/
│   ├── raw/ventes_raw.csv              données brutes (avec anomalies/NA)
│   ├── processed/dataset_clean.csv     dataset nettoyé
│   ├── documents/faq_ecommerce.md      base documentaire (RAG)
│   └── generate_dataset.py
├── src/
│   ├── analytics/  kpi_calculation.py · dashboard.py
│   ├── chatbot/    chatbot_engine.py · rag_pipeline.py · prompts.py · api_chatbot.py · evaluate.py
│   ├── security/   auth.py · security_rules.py · logs.py · attack_tests.py
│   └── app.py                          application intégrée (Streamlit)
├── tests/          test_kpi.py · test_security.py · test_chatbot.py
├── docs/           research_report.md · architecture.md · meeting_notes.md
├── notebooks/      data_analysis.ipynb · model_tests.ipynb
├── data_dictionary.xlsx · access_control_matrix.xlsx
├── liste_questions_metier.docx · security_report.docx
├── evaluation_results.csv · attack_tests.csv
├── requirements.txt
└── README.md
```

## Approche technique

- **Chatbot** : détection d'intention par règles (mots-clés normalisés FR),
  routage vers KPI, tendances, anomalies, ou RAG documentaire.
- **RAG** : recherche TF-IDF + similarité cosinus sur les passages de la FAQ
  (remplaçable par FAISS/ChromaDB sans changer le contrat).
- **Sécurité** : filtre par motifs (regex) + matrice de rôles + logs.
- **BI** : KPI calculés avec pandas, dashboard Plotly/Streamlit.
