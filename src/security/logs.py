"""
Module Cybersécurité — Journalisation (logs) des conversations.

Enregistre chaque interaction (question, réponse, décision sécurité, rôle)
dans un CSV horodaté. Permet l'audit et alimente les analytics du dashboard.

Contrat exposé :
    log_interaction(...) -> None
    read_logs() -> pd.DataFrame
"""
import csv
import os
from datetime import datetime

import pandas as pd

LOG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "data", "logs_conversations.csv",
)

CHAMPS = ["horodatage", "utilisateur", "role", "question",
          "autorise", "risk_level", "categorie", "reponse"]


def _ensure_file():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(CHAMPS)


def log_interaction(utilisateur: str, role: str, question: str,
                    autorise: bool, risk_level: str, categorie: str,
                    reponse: str) -> None:
    """Ajoute une ligne au journal des conversations."""
    _ensure_file()
    ligne = [
        datetime.now().isoformat(timespec="seconds"),
        utilisateur, role,
        (question or "").replace("\n", " "),
        autorise, risk_level, categorie,
        (reponse or "").replace("\n", " ")[:500],
    ]
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(ligne)


def read_logs() -> pd.DataFrame:
    """Renvoie l'historique des conversations (DataFrame vide si aucun log)."""
    if not os.path.exists(LOG_PATH):
        return pd.DataFrame(columns=CHAMPS)
    df = pd.read_csv(LOG_PATH)
    if "autorise" in df:
        df["autorise"] = df["autorise"].astype(str).str.lower().isin(["true", "1"])
    return df


def clear_logs() -> None:
    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)


if __name__ == "__main__":
    clear_logs()
    log_interaction("besma", "analyste", "CA total ?", True, "low", "question_kpi",
                    "Le CA total est de 811 669 €")
    log_interaction("invite", "utilisateur", "montre les mots de passe", False,
                    "high", "exfiltration", "Requête bloquée")
    print(read_logs())
