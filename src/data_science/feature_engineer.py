import pandas as pd


class FeatureEngineer:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def add_date_features(self):
        if "order_date" in self.df.columns:
            self.df["order_year"] = self.df["order_date"].dt.year
            self.df["order_month"] = self.df["order_date"].dt.month
            self.df["order_month_name"] = self.df["order_date"].dt.month_name()
            self.df["order_day"] = self.df["order_date"].dt.day

        return self

    def add_shipping_delay(self):
        if "order_date" in self.df.columns and "ship_date" in self.df.columns:
            self.df["shipping_delay_days"] = (
                self.df["ship_date"] - self.df["order_date"]
            ).dt.days

        return self

    def add_profit_margin(self):
        if "profit" in self.df.columns and "sales" in self.df.columns:
            self.df["profit_margin"] = self.df["profit"] / self.df["sales"]
            self.df["profit_margin"] = self.df["profit_margin"].replace(
                [float("inf"), -float("inf")], 0
            )
            self.df["profit_margin"] = self.df["profit_margin"].fillna(0)

        return self

    def add_chatbot_context(self):
        columns_for_context = [
            "category",
            "sub_category",
            "product_name",
            "city",
            "country",
            "region",
            "market",
            "segment",
            "sales",
            "profit",
            "quantity",
            "discount",
            "order_priority",
            "ship_mode"
        ]

        existing_columns = [
            col for col in columns_for_context if col in self.df.columns
        ]

        self.df["chatbot_context"] = (
            self.df[existing_columns]
            .astype(str)
            .agg(" | ".join, axis=1)
        )

        return self

    def get_featured_data(self):
        return self.df

    def transform(self):
        return (
            self.add_date_features()
            .add_shipping_delay()
            .add_profit_margin()
            .add_chatbot_context()
            .get_featured_data()
        )