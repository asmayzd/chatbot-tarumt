from pathlib import Path
import pandas as pd


class DataLoader:
    def __init__(self, file_path: str, encoding: str = "latin1"):
        self.file_path = Path(file_path)
        self.encoding = encoding

    def load_csv(self) -> pd.DataFrame:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Dataset not found: {self.file_path}")

        return pd.read_csv(self.file_path, encoding=self.encoding)