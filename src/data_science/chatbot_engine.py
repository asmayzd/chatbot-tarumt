import pandas as pd


class ChatbotEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def answer(self, question: str) -> str:
        question = question.lower()

        # Nouvelle détection pour la commande la plus chère (Use case test)
        if self._is_most_expensive_question(question):
            return self._answer_most_expensive()

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
            "Please ask a question about sales, profit, countries, categories, shipping delay, or your most expensive purchase."
        )

    # --- FONCTIONS DE DÉTECTION DES QUESTIONS ---

    def _is_most_expensive_question(self, question: str) -> bool:
        return (
            "most expensive" in question 
            or "plus cher" in question 
            or "highest sales item" in question
            or "highest purchase" in question
        )

    def _is_total_sales_question(self, question: str) -> bool:
        return "total sales" in question or "ventes totales" in question or "my sales" in question

    def _is_total_profit_question(self, question: str) -> bool:
        return "total profit" in question or "profit total" in question

    def _is_highest_sales_country_question(self, question: str) -> bool:
        return (
            "highest sales country" in question
            or "most sales country" in question
            or "plus de ventes" in question
        )

    def _is_most_profitable_country_question(self, question: str) -> bool:
        return (
            "most profitable country" in question
            or "pays le plus rentable" in question
        )

    def _is_most_profitable_category_question(self, question: str) -> bool:
        return (
            "most profitable category" in question
            or "catégorie la plus rentable" in question
        )

    def _is_best_selling_category_question(self, question: str) -> bool:
        return (
            "best selling category" in question
            or "catégorie avec le plus de ventes" in question
        )

    def _is_average_shipping_delay_question(self, question: str) -> bool:
        return (
            "average shipping delay" in question
            or "average delivery delay" in question
            or "délai moyen de livraison" in question
        )

    # --- MOTEURS DE RÉPONSES ROBUSTES (SCANNENT LES COLONNES) ---

    def _find_column(self, candidates: list) -> str:
        """Trouve dynamiquement la colonne correspondante dans le DataFrame."""
        for col in candidates:
            if col in self.df.columns:
                return col
        return None

    def _answer_most_expensive(self) -> str:
        sales_col = self._find_column(["Sales", "sales", "SALES"])
        prod_col = self._find_column(["Product.Name", "Product Name", "product_name", "product", "Product"])
        
        if not sales_col:
            return "Error: Sales column could not be found."
        if not prod_col:
            # Si aucune colonne produit n'est trouvée, on prend la première de type text/object
            text_cols = self.df.select_dtypes(include=['object']).columns
            prod_col = text_cols[0] if len(text_cols) > 0 else self.df.columns[0]
            
        if self.df.empty:
            return "No purchase history available for your profile."
            
        top_purchase = self.df.sort_values(by=sales_col, ascending=False).iloc[0]
        product_name = top_purchase[prod_col]
        price = top_purchase[sales_col]
        
        return f"Your most expensive purchase is '{product_name}' with an amount of {price:,.2f}."

    def _answer_total_sales(self) -> str:
        col = self._find_column(["Sales", "sales", "SALES"])
        if not col:
            return "Error: Sales column not found."
        total_sales = self.df[col].sum()
        return f"The total sales in your dataset are {total_sales:,.2f}."

    def _answer_total_profit(self) -> str:
        col = self._find_column(["Profit", "profit", "PROFIT"])
        if not col:
            return "Error: Profit column not found."
        total_profit = self.df[col].sum()
        return f"The total profit in your dataset is {total_profit:,.2f}."

    def _answer_highest_sales_country(self) -> str:
        country_col = self._find_column(["Country", "country", "COUNTRY"])
        sales_col = self._find_column(["Sales", "sales", "SALES"])
        
        if not country_col or not sales_col:
            return "Error: Country or Sales column missing."
            
        result = self.df.groupby(country_col)[sales_col].sum().sort_values(ascending=False).head(1)
        if result.empty:
            return "No country data available."
        return f"The country with the highest sales is {result.index[0]}, with {result.iloc[0]:,.2f}."

    def _answer_most_profitable_country(self) -> str:
        country_col = self._find_column(["Country", "country", "COUNTRY"])
        profit_col = self._find_column(["Profit", "profit", "PROFIT"])
        
        if not country_col or not profit_col:
            return "Error: Country or Profit column missing."
            
        result = self.df.groupby(country_col)[profit_col].sum().sort_values(ascending=False).head(1)
        if result.empty:
            return "No country data available."
        return f"The most profitable country is {result.index[0]}, with {result.iloc[0]:,.2f}."

    def _answer_most_profitable_category(self) -> str:
        cat_col = self._find_column(["Category", "category", "CATEGORY"])
        profit_col = self._find_column(["Profit", "profit", "PROFIT"])
        
        if not cat_col or not profit_col:
            return "Error: Category or Profit column missing."
            
        result = self.df.groupby(cat_col)[profit_col].sum().sort_values(ascending=False).head(1)
        if result.empty:
            return "No category data available."
        return f"The most profitable category is {result.index[0]}, with {result.iloc[0]:,.2f}."

    def _answer_best_selling_category(self) -> str:
        cat_col = self._find_column(["Category", "category", "CATEGORY"])
        sales_col = self._find_column(["Sales", "sales", "SALES"])
        
        if not cat_col or not sales_col:
            return "Error: Category or Sales column missing."
            
        result = self.df.groupby(cat_col)[sales_col].sum().sort_values(ascending=False).head(1)
        if result.empty:
            return "No category data available."
        return f"The best-selling category is {result.index[0]}, with {result.iloc[0]:,.2f}."

    def _answer_average_shipping_delay(self) -> str:
        delay_col = self._find_column(["shipping_delay_days", "shipping_delay", "delay"])
        if not delay_col:
            return "The shipping delay information is not available in the dataset."

        average_delay = self.df[delay_col].mean()
        return f"The average shipping delay is {average_delay:.2f} days."
