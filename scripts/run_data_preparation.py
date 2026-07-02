import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from data.dataset_loader import DatasetLoader
from src.data_science.data_cleaner import DataCleaner
from src.data_science.feature_engineer import FeatureEngineer


PROCESSED_DATA_PATH = Path("data/dataset_clean.csv")


def main():
    print("Loading dataset...")
    loader = DatasetLoader()
    df = loader.load_csv()

    print("Cleaning dataset...")
    cleaner = DataCleaner(df)
    clean_df = cleaner.clean()

    print("Creating features...")
    feature_engineer = FeatureEngineer(clean_df)
    final_df = feature_engineer.transform()

    final_df.to_csv(PROCESSED_DATA_PATH, index=False)

    print("Data preparation completed.")
    print(f"Rows: {len(final_df)}")
    print(f"Columns: {len(final_df.columns)}")
    print(f"Saved file: {PROCESSED_DATA_PATH}")


if __name__ == "__main__":
    main()