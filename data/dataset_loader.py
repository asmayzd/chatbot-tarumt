import os
import pandas as pd
import kagglehub


class SuperstoreDataLoader:
    """
    Class responsible for downloading and loading
    the Global Superstore dataset.
    """

    def __init__(self, dataset_name: str, file_name: str):
        self.dataset_name = dataset_name
        self.file_name = file_name
        self.dataset_path = None
        self.csv_path = None
        self.dataframe = None

    def download_dataset(self):
        """
        Download the dataset from Kaggle.
        """
        self.dataset_path = kagglehub.dataset_download(self.dataset_name)
        print("Path to dataset files:", self.dataset_path)
        return self.dataset_path

    def show_available_files(self):
        """
        Display the available files in the downloaded dataset folder.
        """
        if self.dataset_path is None:
            raise ValueError("The dataset must be downloaded before displaying files.")

        files = os.listdir(self.dataset_path)
        print("Available files:", files)
        return files

    def load_csv(self):
        """
        Load the CSV file into a pandas DataFrame.
        """
        if self.dataset_path is None:
            self.download_dataset()

        self.csv_path = os.path.join(self.dataset_path, self.file_name)

        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(
                f"The file '{self.file_name}' was not found. "
                f"Check the exact file name using show_available_files()."
            )

        self.dataframe = pd.read_csv(self.csv_path, encoding="latin1")
        return self.dataframe

    def show_overview(self):
        """
        Display a quick overview of the dataset.
        """
        if self.dataframe is None:
            raise ValueError("The data must be loaded before displaying an overview.")

        print("\n===== DATA PREVIEW =====")
        print(self.dataframe.head())

        print("\n===== COLUMNS =====")
        print(self.dataframe.columns)

        print("\n===== SHAPE =====")
        print(self.dataframe.shape)