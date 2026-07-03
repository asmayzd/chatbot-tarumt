import sys
from pathlib import Path
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))
from src.bi_analytics.kpi_analyzer import KPIAnalyzer

from src.bi_analytics.anomaly_detector import AnomalyDetector
DATASET_PATH = Path("data/dataset_clean.csv")


class AutomatedReportingWorkflow:
    def __init__(self, dataset_path: Path):
        self.dataset_path = dataset_path
        self.df = None

    def load_dataset(self):
        if not self.dataset_path.exists():
            raise FileNotFoundError(
                f"Dataset not found: {self.dataset_path}. "
                "Please run scripts/run_data_preparation.py first."
            )

        self.df = pd.read_csv(self.dataset_path)
        return self

    def display_dataset_overview(self):
        print("\n===== DATASET OVERVIEW =====")
        print(f"Rows: {self.df.shape[0]}")
        print(f"Columns: {self.df.shape[1]}")

        print("\nColumns:")
        print(list(self.df.columns))

        return self

    def display_basic_kpis(self):
        print("\n===== BASIC KPI REPORT =====")

        kpi_analyzer = KPIAnalyzer(self.df)
        kpis = kpi_analyzer.get_main_kpis()

        print(f"Total sales: {kpis['total_sales']:,.2f}")
        print(f"Total profit: {kpis['total_profit']:,.2f}")
        print(f"Total quantity sold: {kpis['total_quantity']:,}")
        print(f"Average discount: {kpis['average_discount']:.2%}")
        print(f"Average profit margin: {kpis['average_profit_margin']:.2%}")
        print(f"Average shipping delay: {kpis['average_shipping_delay']:.2f} days")

        return self

    def display_top_countries_by_sales(self, top_n=5):
        print("\n===== TOP COUNTRIES BY SALES =====")

        kpi_analyzer = KPIAnalyzer(self.df)
        top_countries = kpi_analyzer.sales_by_country().head(top_n)

        print(top_countries)

        return self
    
    def display_top_categories_by_profit(self):
        print("\n===== PROFIT BY CATEGORY =====")

        kpi_analyzer = KPIAnalyzer(self.df)
        category_profit = kpi_analyzer.profit_by_category()

        print(category_profit)

        return self

    def display_basic_anomalies(self):
        print("\n===== ANOMALY DETECTION REPORT =====")

        anomaly_detector = AnomalyDetector(self.df)
        report = anomaly_detector.get_anomaly_report()

        print(
            "High sales with negative profit:",
             report["high_sales_negative_profit_count"]
         )

        print(
            "High discount with negative profit:",
             report["high_discount_negative_profit_count"]
        )

        print(
            "Long shipping delay orders:",
            report["long_shipping_delay_count"]
        )

        print(
            "Unusual sales values:",
            report["unusual_sales_values_count"]
        )

        print("\nTop unprofitable products:")
        print(report["unprofitable_products"])

        print("\nCountries with lowest profit margin:")
        print(report["low_margin_countries"])

        return self

    def generate_simple_executive_summary(self):
        print("\n===== EXECUTIVE SUMMARY =====")

        total_sales = self.df["sales"].sum()
        total_profit = self.df["profit"].sum()

        top_country = (
            self.df.groupby("country")["sales"]
            .sum()
            .sort_values(ascending=False)
            .head(1)
        )

        top_category = (
            self.df.groupby("category")["profit"]
            .sum()
            .sort_values(ascending=False)
            .head(1)
        )

        summary = []

        summary.append(
            f"The dataset generated total sales of {total_sales:,.2f} "
            f"and total profit of {total_profit:,.2f}."
        )

        if not top_country.empty:
            summary.append(
                f"The leading country by sales is {top_country.index[0]}, "
                f"with {top_country.iloc[0]:,.2f} in sales."
            )

        if not top_category.empty:
            summary.append(
                f"The most profitable category is {top_category.index[0]}, "
                f"with {top_category.iloc[0]:,.2f} in profit."
            )

        print(" ".join(summary))

        return self

    def run(self):
        return (
            self.load_dataset()
            .display_dataset_overview()
            .display_basic_kpis()
            .display_top_countries_by_sales()
            .display_top_categories_by_profit()
            .display_basic_anomalies()
            .generate_simple_executive_summary()
        )


def main():
    workflow = AutomatedReportingWorkflow(DATASET_PATH)
    workflow.run()


if __name__ == "__main__":
    main()