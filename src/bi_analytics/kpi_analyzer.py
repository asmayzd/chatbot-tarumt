import pandas as pd


class KPIAnalyzer:
    """
    Class responsible for calculating business KPIs
    from the cleaned Superstore dataset.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def total_sales(self) -> float:
        return self.df["sales"].sum()

    def total_profit(self) -> float:
        return self.df["profit"].sum()

    def total_quantity(self) -> int:
        return self.df["quantity"].sum()

    def average_discount(self) -> float:
        return self.df["discount"].mean()

    def average_profit_margin(self) -> float:
        if "profit_margin" not in self.df.columns:
            return 0.0

        return self.df["profit_margin"].mean()

    def average_shipping_delay(self) -> float:
        if "shipping_delay_days" not in self.df.columns:
            return 0.0

        return self.df["shipping_delay_days"].mean()

    def sales_by_country(self) -> pd.Series:
        return (
            self.df.groupby("country")["sales"]
            .sum()
            .sort_values(ascending=False)
        )

    def profit_by_country(self) -> pd.Series:
        return (
            self.df.groupby("country")["profit"]
            .sum()
            .sort_values(ascending=False)
        )

    def sales_by_category(self) -> pd.Series:
        return (
            self.df.groupby("category")["sales"]
            .sum()
            .sort_values(ascending=False)
        )

    def profit_by_category(self) -> pd.Series:
        return (
            self.df.groupby("category")["profit"]
            .sum()
            .sort_values(ascending=False)
        )

    def sales_by_market(self) -> pd.Series:
        return (
            self.df.groupby("market")["sales"]
            .sum()
            .sort_values(ascending=False)
        )

    def profit_by_market(self) -> pd.Series:
        return (
            self.df.groupby("market")["profit"]
            .sum()
            .sort_values(ascending=False)
        )

    def top_products_by_sales(self, top_n: int = 10) -> pd.Series:
        return (
            self.df.groupby("product_name")["sales"]
            .sum()
            .sort_values(ascending=False)
            .head(top_n)
        )

    def top_products_by_profit(self, top_n: int = 10) -> pd.Series:
        return (
            self.df.groupby("product_name")["profit"]
            .sum()
            .sort_values(ascending=False)
            .head(top_n)
        )

    def worst_products_by_profit(self, top_n: int = 10) -> pd.Series:
        return (
            self.df.groupby("product_name")["profit"]
            .sum()
            .sort_values(ascending=True)
            .head(top_n)
        )

    def get_main_kpis(self) -> dict:
        """
        Returns the main KPIs in a dictionary.
        This will be used by the automated reporting workflow.
        """
        return {
            "total_sales": self.total_sales(),
            "total_profit": self.total_profit(),
            "total_quantity": self.total_quantity(),
            "average_discount": self.average_discount(),
            "average_profit_margin": self.average_profit_margin(),
            "average_shipping_delay": self.average_shipping_delay(),
        }