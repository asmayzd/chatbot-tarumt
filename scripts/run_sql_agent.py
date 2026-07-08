import os
import sys
import configparser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

import pandas as pd

from src.bi_analytics.sql_agent import SQLAgent


DATASET_PATH = Path("data/dataset_clean.csv")


def load_api_key():
    """Load GEMINI_API_KEY from config.ini into the environment."""
    config = configparser.ConfigParser()

    if Path("config.ini").exists():
        config.read("config.ini")

        if "API_KEYS" in config and "GEMINI_API_KEY" in config["API_KEYS"]:
            os.environ["GEMINI_API_KEY"] = config["API_KEYS"]["GEMINI_API_KEY"]


def main():
    load_api_key()

    if "GEMINI_API_KEY" not in os.environ:
        print("GEMINI_API_KEY not found. Add it to config.ini under [API_KEYS].")
        return

    if not DATASET_PATH.exists():
        print(
            f"Dataset not found: {DATASET_PATH}. "
            "Please run scripts/run_data_preparation.py first."
        )
        return

    df = pd.read_csv(DATASET_PATH)

    agent = SQLAgent(df).setup()

    print("SQL Agent ready.")
    print("Ask a question in natural language (type 'exit' to quit).")
    print("-" * 60)

    while True:
        question = input("\nYour question: ").strip()

        if question.lower() in {"exit", "quit", "q"}:
            print("Goodbye.")
            break

        if not question:
            continue

        result = agent.ask(question)

        print(f"\nGenerated SQL:\n{result['sql']}")

        if result["error"]:
            print(f"\nError: {result['error']}")
            continue

        print("\nResult:")
        print(result["result"].to_string(index=False))

        answer = agent.explain_result(question, result["result"])
        print(f"\nAnswer:\n{answer}")


if __name__ == "__main__":
    main()
