import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.data_science.chatbot_engine import ChatbotEngine
from src.data_science.chatbot_evaluator import ChatbotEvaluator


DATASET_PATH = Path("data/dataset_clean.csv")


def main():
    df = pd.read_csv(DATASET_PATH)

    chatbot = ChatbotEngine(df)
    evaluator = ChatbotEvaluator(chatbot)

    results = evaluator.run_basic_tests()

    for result in results:
        print("-" * 50)
        print("Question:", result["question"])
        print("Answer:", result["answer"])
        print("Status:", result["status"])


if __name__ == "__main__":
    main()