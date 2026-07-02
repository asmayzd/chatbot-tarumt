import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.data_science.chatbot_engine import ChatbotEngine


DATASET_PATH = Path("data/dataset_clean.csv")


def main():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            "Clean dataset not found. Please run scripts/run_data_preparation.py first."
        )

    df = pd.read_csv(DATASET_PATH)
    chatbot = ChatbotEngine(df)

    print("Chatbot is ready.")
    print("Type 'exit' to stop.")

    while True:
        question = input("\nYou: ")

        if question.lower() in ["exit", "quit"]:
            print("Chatbot stopped.")
            break

        answer = chatbot.answer(question)
        print("Bot:", answer)


if __name__ == "__main__":
    main()