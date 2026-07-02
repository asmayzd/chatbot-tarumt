"""
Module Data Science / ML — Évaluation de la qualité du chatbot.

Compare l'intention détectée à l'intention attendue sur un jeu de test,
mesure la précision globale et écrit evaluation_results.csv.

Lancer :  python src/chatbot/evaluate.py
"""
import csv
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from src.chatbot.chatbot_engine import chatbot_response, detecter_intention

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "..", "evaluation_results.csv")

# Jeu de test : (question, intention_attendue)
JEU_TEST = [
    ("Quel est le chiffre d'affaires total ?", "question_kpi"),
    ("Combien de commandes au total ?", "question_kpi"),
    ("Quel est le panier moyen ?", "question_kpi"),
    ("Quels sont les produits les plus vendus ?", "question_kpi"),
    ("Quelle catégorie rapporte le plus ?", "question_kpi"),
    ("Combien de clients actifs ?", "question_kpi"),
    ("Combien de clients sont inactifs ?", "question_kpi"),
    ("Quel mois a eu les meilleures ventes ?", "question_tendance"),
    ("Comment évoluent les ventes sur l'année ?", "question_tendance"),
    ("Y a-t-il une saisonnalité ?", "question_tendance"),
    ("Y a-t-il des anomalies dans les ventes ?", "question_anomalie"),
    ("Détecte les commandes suspectes", "question_anomalie"),
    ("Quels sont les délais de livraison ?", "question_documentaire"),
    ("Comment faire un retour ?", "question_documentaire"),
    ("Quelle est la garantie sur l'électronique ?", "question_documentaire"),
    ("Quels moyens de paiement acceptez-vous ?", "question_documentaire"),
    ("Bonjour !", "question_generale"),
    ("Merci beaucoup", "question_generale"),
    ("Qui es-tu ?", "question_generale"),
    ("Quelle est la météo demain ?", "question_generale"),
]


def evaluer():
    lignes, corrects = [], 0
    for question, attendu in JEU_TEST:
        rep = chatbot_response(question, "analyste")
        predit = rep["intent"]
        ok = (predit == attendu)
        corrects += ok
        lignes.append({
            "question": question,
            "intention_attendue": attendu,
            "intention_predite": predit,
            "correct": ok,
            "confiance": rep["confidence"],
            "reponse": rep["answer"].splitlines()[0][:80],
        })

    precision = round(corrects / len(JEU_TEST), 3)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)

    print(f"Précision détection d'intention : {precision:.1%} "
          f"({corrects}/{len(JEU_TEST)})")
    print(f"Résultats -> {os.path.abspath(OUT)}")
    return precision


if __name__ == "__main__":
    evaluer()
