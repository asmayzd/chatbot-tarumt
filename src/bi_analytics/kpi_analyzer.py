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

    def _scoped_df(self, start: str | None, end: str | None) -> pd.DataFrame:
        """Filter self.df to an inclusive "YYYY-MM" period range, or return it unchanged."""
        if not start and not end:
            return self.df
        if "order_year" not in self.df.columns or "order_month" not in self.df.columns:
            return self.df

        df = self.df.copy()
        df["period"] = df["order_year"].astype(str) + "-" + df["order_month"].astype(str).str.zfill(2)
        if start:
            df = df[df["period"] >= start]
        if end:
            df = df[df["period"] <= end]
        return df

    def sales_by_country(self, start: str | None = None, end: str | None = None) -> pd.Series:
        return (
            self._scoped_df(start, end).groupby("country")["sales"]
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

    def profit_by_category(self, start: str | None = None, end: str | None = None) -> pd.Series:
        return (
            self._scoped_df(start, end).groupby("category")["profit"]
            .sum()
            .sort_values(ascending=False)
        )

    def sales_by_market(self, start: str | None = None, end: str | None = None) -> pd.Series:
        return (
            self._scoped_df(start, end).groupby("market")["sales"]
            .sum()
            .sort_values(ascending=False)
        )

    def profit_by_market(self) -> pd.Series:
        return (
            self.df.groupby("market")["profit"]
            .sum()
            .sort_values(ascending=False)
        )

    def top_products_by_sales(self, top_n: int = 10, start: str | None = None, end: str | None = None) -> pd.Series:
        return (
            self._scoped_df(start, end).groupby("product_name")["sales"]
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

    def monthly_trends(self, start: str | None = None, end: str | None = None) -> pd.DataFrame:
        """
        Monthly aggregates for sales, profit, and distinct order count.

        start/end are inclusive "YYYY-MM" bounds, or None for no bound.
        Returns a DataFrame with columns: period, year, month, month_name,
        sales, profit, order_count — sorted chronologically.
        """
        columns = ["period", "year", "month", "month_name", "sales", "profit", "order_count"]
        if "order_year" not in self.df.columns or "order_month" not in self.df.columns:
            return pd.DataFrame(columns=columns)

        df = self.df.copy()
        df["period"] = df["order_year"].astype(str) + "-" + df["order_month"].astype(str).str.zfill(2)

        if start:
            df = df[df["period"] >= start]
        if end:
            df = df[df["period"] <= end]

        if df.empty:
            return pd.DataFrame(columns=columns)

        grouped = (
            df.groupby(["order_year", "order_month", "period"])
            .agg(sales=("sales", "sum"), profit=("profit", "sum"), order_count=("order_id", "nunique"))
            .reset_index()
        )
        grouped["month_name"] = pd.to_datetime(grouped["period"], format="%Y-%m").dt.strftime("%B")
        grouped = grouped.rename(columns={"order_year": "year", "order_month": "month"})
        return grouped.sort_values("period")[columns].reset_index(drop=True)

    def profit_by_category_monthly(self, start: str | None = None, end: str | None = None) -> pd.DataFrame:
        """
        Monthly profit per category (long format), for a multi-line trend chart.

        Returns columns: period, year, month, month_name, category, profit.
        """
        columns = ["period", "year", "month", "month_name", "category", "profit"]
        if "order_year" not in self.df.columns or "order_month" not in self.df.columns:
            return pd.DataFrame(columns=columns)

        # _scoped_df returns self.df unchanged (not a copy) when no start/end is
        # given, so copy() here rather than mutate the shared singleton frame.
        df = self._scoped_df(start, end).copy()
        df["period"] = df["order_year"].astype(str) + "-" + df["order_month"].astype(str).str.zfill(2)

        if df.empty:
            return pd.DataFrame(columns=columns)

        grouped = (
            df.groupby(["order_year", "order_month", "period", "category"])["profit"]
            .sum()
            .reset_index()
        )
        grouped["month_name"] = pd.to_datetime(grouped["period"], format="%Y-%m").dt.strftime("%B")
        grouped = grouped.rename(columns={"order_year": "year", "order_month": "month"})
        return grouped.sort_values(["period", "category"])[columns].reset_index(drop=True)

    def available_month_range(self) -> tuple[str | None, str | None]:
        """Min/max 'YYYY-MM' present in the data, used to bound frontend month pickers."""
        if "order_year" not in self.df.columns or "order_month" not in self.df.columns:
            return None, None
        periods = self.df["order_year"].astype(str) + "-" + self.df["order_month"].astype(str).str.zfill(2)
        if periods.empty:
            return None, None
        return periods.min(), periods.max()

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