"""
Module Data Science / ML — Moteur du chatbot.

Pipeline : question -> détection d'intention -> routage (KPI / RAG / général)
-> réponse formatée.

Contrat exposé (le cœur de l'intégration) :
    chatbot_response(user_question: str, user_role: str) -> dict
    -> {"answer", "source", "confidence", "category", "intent"}
"""
import os
import sys
import unicodedata

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from src.analytics import kpi_calculation as kpi
from src.chatbot import rag_pipeline, prompts
from src.security import auth as _auth


def _normaliser(texte: str) -> str:
    """Minuscule + suppression des accents + ponctuation -> espaces."""
    texte = (texte or "").lower()
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    texte = "".join(c if c.isalnum() else " " for c in texte)
    texte = " ".join(texte.split())
    return " " + texte + " "


def detecter_intention(question: str) -> str:
    """Détermine l'intention à partir de mots-clés (NLP par règles)."""
    q = _normaliser(question)
    # priorité : anomalie > tendance > documentaire > kpi > général
    for intent in ["question_anomalie", "question_tendance",
                   "question_documentaire", "question_kpi", "question_generale"]:
        for kw in prompts.MOTS_CLES.get(intent, []):
            kw_norm = _normaliser(kw).strip()
            if kw_norm and kw_norm in q:
                return intent
    return "question_generale"


def _trouver_metrique(question: str) -> str:
    """Associe la question à une métrique get_kpi() précise."""
    q = _normaliser(question)
    # on cherche la clé de mapping la plus spécifique présente dans la question
    meilleur = None
    for cle, metrique in prompts.KPI_MAPPING.items():
        if _normaliser(cle).strip() in q:
            if meilleur is None or len(cle) > len(meilleur[0]):
                meilleur = (cle, metrique)
    return meilleur[1] if meilleur else "total_revenue"


def _repondre_kpi(question: str) -> dict:
    metrique = _trouver_metrique(question)
    res = kpi.get_kpi(metrique)
    gabarit = prompts.GABARITS.get(metrique, "{value}")
    try:
        if metrique == "best_month":
            texte = gabarit.format(value=res["value"], ca=res["detail"]["ca"])
        else:
            texte = gabarit.format(value=res["value"])
    except (KeyError, ValueError, TypeError):
        texte = f"{res['metric']} : {res['value']}"

    # enrichissement : détail top produits / catégories
    if metrique == "top_products" and res["detail"]:
        lignes = [f"  - {d['produit']} : {d['unites_vendues']} unités"
                  for d in res["detail"][:5]]
        texte += "\nTop 5 :\n" + "\n".join(lignes)
    if metrique in ("revenue_by_category", "revenue_by_region") and res["detail"]:
        col = "categorie" if metrique == "revenue_by_category" else "region"
        lignes = [f"  - {d[col]} : {d['ca']:,.0f} €" for d in res["detail"][:5]]
        texte += "\nDétail :\n" + "\n".join(lignes)

    return {"answer": texte, "source": "dataset_clean.csv",
            "confidence": 0.95, "metric": metrique}


def _repondre_general(question: str) -> dict:
    q = _normaliser(question)
    if any(m in q for m in [" bonjour ", " salut ", " coucou ", " ca va ", " hello ", " bonsoir "]):
        rep = ("Bonjour ! Je suis l'assistant d'analyse e-commerce. "
               "Posez-moi une question sur le chiffre d'affaires, les produits, "
               "les clients, les tendances ou la politique de livraison/retour.")
    elif " merci " in q:
        rep = "Avec plaisir !"
    elif any(m in q for m in [" aide ", " help ", " qui es tu ", " que sais tu "]):
        rep = ("Je peux répondre à des questions métier (CA, produits populaires, "
               "meilleur mois, clients inactifs, anomalies) et à des questions "
               "documentaires (livraison, retours, garantie, paiement).")
    else:
        rep = ("Je n'ai pas bien compris la question. Essayez par exemple : "
               "« Quel est le chiffre d'affaires total ? » ou "
               "« Quels sont les produits les plus vendus ? ».")
    return {"answer": rep, "source": None, "confidence": 0.4, "metric": None}


def chatbot_response(user_question: str, user_role: str = "utilisateur") -> dict:
    """
    Contrat principal du chatbot.
    NB : la vérification de sécurité est faite EN AMONT par le module cyber
    (check_security). Ici on suppose la question déjà autorisée.
    """
    intent = detecter_intention(user_question)
    q_norm = _normaliser(user_question)

    # Cas particulier : demande de données clients nominatives (PII).
    # La sécurité a déjà autorisé l'accès en amont ; on ne sert la fiche
    # que si le rôle possède réellement le droit clients_pii.
    demande_pii = ("personnel" in q_norm or "coordonnees" in q_norm
                   or ("liste" in q_norm and "client" in q_norm)
                   or "fiche client" in q_norm)
    if demande_pii and _auth.can_access(user_role, "clients_pii"):
        fiche = kpi.fiche_clients(10)
        lignes = [f"  - {r['id_client']} : {r['nb_commandes']} commandes, "
                  f"{r['ca']:,.0f} € (dernier achat {r['dernier_achat']})"
                  for _, r in fiche.iterrows()]
        texte = "Top 10 clients par CA :\n" + "\n".join(lignes)
        return {"answer": texte, "source": "dataset_clean.csv",
                "confidence": 0.9, "category": "question_kpi",
                "intent": "question_kpi"}

    if intent in ("question_kpi", "question_tendance", "question_anomalie"):
        # tendance/anomalie sont des sous-cas de KPI (même source de données)
        if intent == "question_anomalie":
            res = kpi.get_kpi("anomalies")
            texte = prompts.GABARITS["anomalies"].format(value=res["value"])
            if res["detail"]:
                lignes = [f"  - {d['produit']} (commande {d['id_commande']}) : "
                          f"{d['montant']} €" for d in res["detail"][:5]]
                texte += "\nExemples :\n" + "\n".join(lignes)
            out = {"answer": texte, "source": "dataset_clean.csv",
                   "confidence": 0.9, "metric": "anomalies"}
        elif intent == "question_tendance":
            mm = kpi.get_kpi("best_month")
            texte = prompts.GABARITS["best_month"].format(
                value=mm["value"], ca=mm["detail"]["ca"])
            out = {"answer": texte, "source": "dataset_clean.csv",
                   "confidence": 0.9, "metric": "best_month"}
        else:
            out = _repondre_kpi(user_question)
        out.update({"category": intent, "intent": intent})
        return out

    if intent == "question_documentaire":
        r = rag_pipeline.answer_from_docs(user_question)
        return {"answer": r["answer"], "source": r["source"],
                "confidence": r["confidence"],
                "category": "question_documentaire",
                "intent": "question_documentaire"}

    r = _repondre_general(user_question)
    return {"answer": r["answer"], "source": r["source"],
            "confidence": r["confidence"],
            "category": "question_generale", "intent": "question_generale"}


if __name__ == "__main__":
    exemples = [
        "Quel est le chiffre d'affaires total ?",
        "Quels sont les produits les plus vendus ?",
        "Quel mois a eu les meilleures ventes ?",
        "Combien de clients sont inactifs ?",
        "Y a-t-il des anomalies dans les ventes ?",
        "Quels sont les délais de livraison ?",
        "Bonjour, tu peux m'aider ?",
        "Quel est le CA par catégorie ?",
    ]
    for q in exemples:
        r = chatbot_response(q, "analyste")
        print(f"\nQ: {q}\n[{r['intent']}] {r['answer'].splitlines()[0]}")
