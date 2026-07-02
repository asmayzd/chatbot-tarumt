import pandas as pd


class DataCleaner:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def clean_column_names(self):
        self.df.columns = (
            self.df.columns
            .str.strip()
            .str.replace(".", "_", regex=False)
            .str.replace(" ", "_", regex=False)
            .str.lower()
        )
        return self

    def remove_unnecessary_columns(self):
        columns_to_drop = []

        if "记录数" in self.df.columns:
            columns_to_drop.append("记录数")

        if columns_to_drop:
            self.df = self.df.drop(columns=columns_to_drop)

        return self

    def remove_duplicates(self):
        self.df = self.df.drop_duplicates()
        return self

    def clean_text_columns(self):
        text_columns = self.df.select_dtypes(include=["object"]).columns

        for col in text_columns:
            self.df[col] = (
                self.df[col]
                .astype(str)
                .str.strip()
                .str.replace(r"\s+", " ", regex=True)
            )

        return self

    def convert_dates(self):
        date_columns = ["order_date", "ship_date"]

        for col in date_columns:
            if col in self.df.columns:
                self.df[col] = pd.to_datetime(self.df[col], errors="coerce")

        existing_dates = [col for col in date_columns if col in self.df.columns]

        if existing_dates:
            self.df = self.df.dropna(subset=existing_dates)

        return self

    def convert_numeric_columns(self):
        numeric_columns = [
            "sales",
            "profit",
            "discount",
            "quantity",
            "shipping_cost"
        ]

        for col in numeric_columns:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors="coerce")

        existing_numeric = [col for col in numeric_columns if col in self.df.columns]

        if existing_numeric:
            self.df = self.df.dropna(subset=existing_numeric)

        return self

    def get_clean_data(self):
        return self.df

    def clean(self):
        return (
            self.clean_column_names()
            .remove_unnecessary_columns()
            .remove_duplicates()
            .clean_text_columns()
            .convert_dates()
            .convert_numeric_columns()
            .get_clean_data()
        )