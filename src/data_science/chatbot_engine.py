import pandas as pd


class ChatbotEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def answer(self, question: str) -> str:
        question = question.lower()

        if self._is_total_sales_question(question):
            return self._answer_total_sales()

        if self._is_total_profit_question(question):
            return self._answer_total_profit()

        if self._is_highest_sales_country_question(question):
            return self._answer_highest_sales_country()

        if self._is_most_profitable_country_question(question):
            return self._answer_most_profitable_country()

        if self._is_most_profitable_category_question(question):
            return self._answer_most_profitable_category()

        if self._is_best_selling_category_question(question):
            return self._answer_best_selling_category()

        if self._is_average_shipping_delay_question(question):
            return self._answer_average_shipping_delay()

        return (
            "I cannot answer this question yet. "
            "Please ask a question about sales, profit, countries, categories, or shipping delay."
        )

    def _is_total_sales_question(self, question: str) -> bool:
        return "total sales" in question or "ventes totales" in question

    def _is_total_profit_question(self, question: str) -> bool:
        return "total profit" in question or "profit total" in question

    def _is_highest_sales_country_question(self, question: str) -> bool:
        return (
            "highest sales" in question
            or "most sales" in question
            or "plus de ventes" in question
            or "meilleures ventes" in question
        )

    def _is_most_profitable_country_question(self, question: str) -> bool:
        return (
            "most profitable country" in question
            or "country with highest profit" in question
            or "pays le plus rentable" in question
        )

    def _is_most_profitable_category_question(self, question: str) -> bool:
        return (
            "most profitable category" in question
            or "category with highest profit" in question
            or "catégorie la plus rentable" in question
        )

    def _is_best_selling_category_question(self, question: str) -> bool:
        return (
            "best selling category" in question
            or "category with highest sales" in question
            or "catégorie avec le plus de ventes" in question
        )

    def _is_average_shipping_delay_question(self, question: str) -> bool:
        return (
            "average shipping delay" in question
            or "average delivery delay" in question
            or "délai moyen de livraison" in question
        )

    def _answer_total_sales(self) -> str:
        total_sales = self.df["sales"].sum()
        return f"The total sales in the dataset are {total_sales:,.2f}."

    def _answer_total_profit(self) -> str:
        total_profit = self.df["profit"].sum()
        return f"The total profit in the dataset is {total_profit:,.2f}."

    def _answer_highest_sales_country(self) -> str:
        result = (
            self.df.groupby("country")["sales"]
            .sum()
            .sort_values(ascending=False)
            .head(1)
        )

        country = result.index[0]
        sales = result.iloc[0]

        return f"The country with the highest sales is {country}, with {sales:,.2f} in sales."

    def _answer_most_profitable_country(self) -> str:
        result = (
            self.df.groupby("country")["profit"]
            .sum()
            .sort_values(ascending=False)
            .head(1)
        )

        country = result.index[0]
        profit = result.iloc[0]

        return f"The most profitable country is {country}, with {profit:,.2f} in profit."

    def _answer_most_profitable_category(self) -> str:
        result = (
            self.df.groupby("category")["profit"]
            .sum()
            .sort_values(ascending=False)
            .head(1)
        )

        category = result.index[0]
        profit = result.iloc[0]

        return f"The most profitable category is {category}, with {profit:,.2f} in profit."

    def _answer_best_selling_category(self) -> str:
        result = (
            self.df.groupby("category")["sales"]
            .sum()
            .sort_values(ascending=False)
            .head(1)
        )

        category = result.index[0]
        sales = result.iloc[0]

        return f"The best-selling category is {category}, with {sales:,.2f} in sales."

    def _answer_average_shipping_delay(self) -> str:
        if "shipping_delay_days" not in self.df.columns:
            return "The shipping delay information is not available in the dataset."

        average_delay = self.df["shipping_delay_days"].mean()

        return f"The average shipping delay is {average_delay:.2f} days."