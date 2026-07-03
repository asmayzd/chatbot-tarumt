import pandas as pd


class AnomalyDetector:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def high_sales_negative_profit(self) -> pd.DataFrame:
        """
        Detect orders with high sales but negative profit.
        These orders generate revenue but lose money.
        """
        sales_threshold = self.df["sales"].quantile(0.75)

        return self.df[
            (self.df["sales"] >= sales_threshold)
            & (self.df["profit"] < 0)
        ]

    def high_discount_negative_profit(self) -> pd.DataFrame:
        """
        Detect orders with high discount and negative profit.
        This can indicate that discounts are damaging profitability.
        """
        return self.df[
            (self.df["discount"] >= 0.30)
            & (self.df["profit"] < 0)
        ]

    def long_shipping_delay(self) -> pd.DataFrame:
        """
        Detect orders with unusually long shipping delays.
        """
        if "shipping_delay_days" not in self.df.columns:
            return pd.DataFrame()

        delay_threshold = self.df["shipping_delay_days"].quantile(0.90)

        return self.df[
            self.df["shipping_delay_days"] >= delay_threshold
        ]

    def unprofitable_products(self, top_n: int = 10) -> pd.Series:
        """
        Return products with the lowest total profit.
        """
        return (
            self.df.groupby("product_name")["profit"]
            .sum()
            .sort_values(ascending=True)
            .head(top_n)
        )

    def low_margin_countries(self, top_n: int = 10) -> pd.Series:
        """
        Detect countries with the lowest average profit margin.
        """
        if "profit_margin" not in self.df.columns:
            return pd.Series(dtype=float)

        return (
            self.df.groupby("country")["profit_margin"]
            .mean()
            .sort_values(ascending=True)
            .head(top_n)
        )

    def unusual_sales_values(self) -> pd.DataFrame:
        """
        Detect unusually high sales values using the IQR method.
        """
        q1 = self.df["sales"].quantile(0.25)
        q3 = self.df["sales"].quantile(0.75)
        iqr = q3 - q1

        upper_limit = q3 + 1.5 * iqr

        return self.df[self.df["sales"] > upper_limit]

    def get_anomaly_report(self) -> dict:
        """
        Return a summary report of detected anomalies.
        """
        high_sales_losses = self.high_sales_negative_profit()
        discount_losses = self.high_discount_negative_profit()
        shipping_delays = self.long_shipping_delay()
        unusual_sales = self.unusual_sales_values()

        return {
            "high_sales_negative_profit_count": len(high_sales_losses),
            "high_discount_negative_profit_count": len(discount_losses),
            "long_shipping_delay_count": len(shipping_delays),
            "unusual_sales_values_count": len(unusual_sales),
            "unprofitable_products": self.unprofitable_products(5),
            "low_margin_countries": self.low_margin_countries(5),
        }