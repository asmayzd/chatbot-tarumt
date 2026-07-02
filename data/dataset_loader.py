import os
import kagglehub
import pandas as pd


class DatasetLoader:
    def __init__(
        self,
        dataset_name="fatihilhan/global-superstore-dataset",
        file_name="superstore.csv",
        encoding="latin1"
    ):
        self.dataset_name = dataset_name
        self.file_name = file_name
        self.encoding = encoding
        self.dataset_path = None
        self.csv_path = None

    def download_dataset(self):
        self.dataset_path = kagglehub.dataset_download(self.dataset_name)

        print("Path to dataset files:", self.dataset_path)
        print("Available files:", os.listdir(self.dataset_path))

        return self

    def find_csv_file(self):
        if self.dataset_path is None:
            raise ValueError("Dataset must be downloaded first.")

        self.csv_path = os.path.join(self.dataset_path, self.file_name)

        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"File not found: {self.csv_path}")

        return self

    def load_csv(self):
        self.download_dataset()
        self.find_csv_file()

        df = pd.read_csv(self.csv_path, encoding=self.encoding)
        return df