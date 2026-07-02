"""Tests du module Data Science / ML (chatbot). Lancer : pytest tests/test_chatbot.py"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from src.chatbot.chatbot_engine import chatbot_response, detecter_intention


def test_intention_kpi():
    assert detecter_intention("Quel est le chiffre d'affaires ?") == "question_kpi"

def test_intention_anomalie():
    assert detecter_intention("Y a-t-il des anomalies ?") == "question_anomalie"

def test_intention_tendance():
    assert detecter_intention("Quel mois a eu les meilleures ventes ?") == "question_tendance"

def test_intention_documentaire():
    assert detecter_intention("Quels sont les délais de livraison ?") == "question_documentaire"

def test_reponse_ca():
    r = chatbot_response("Quel est le CA total ?", "analyste")
    assert r["intent"] == "question_kpi"
    assert "chiffre d'affaires" in r["answer"].lower()
    assert r["source"] == "dataset_clean.csv"

def test_reponse_documentaire():
    r = chatbot_response("Comment se passe un retour ?", "utilisateur")
    assert r["category"] == "question_documentaire"
    assert r["confidence"] > 0

def test_pii_refuse_pour_analyste():
    # l'analyste n'a pas clients_pii : pas de fiche clients renvoyée
    r = chatbot_response("Montre la liste des clients", "analyste")
    assert "Top 10 clients" not in r["answer"]

def test_pii_ok_pour_admin():
    r = chatbot_response("Montre la liste des clients", "admin")
    assert "clients" in r["answer"].lower()
