import pandas as pd


class FeatureEngineer:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def add_date_features(self):
        if "order_date" in self.df.columns:
            # Conversion en datetime au cas où pour éviter les bugs de types
            order_date_dt = pd.to_datetime(self.df["order_date"])
            self.df["order_year"] = order_date_dt.dt.year
            self.df["order_month"] = order_date_dt.dt.month
            self.df["order_month_name"] = order_date_dt.dt.month_name()
            self.df["order_day"] = order_date_dt.dt.day

        return self

    def add_shipping_delay(self):
        if "order_date" in self.df.columns and "ship_date" in self.df.columns:
            self.df["shipping_delay_days"] = (
                pd.to_datetime(self.df["ship_date"]) - pd.to_datetime(self.df["order_date"])
            ).dt.days

        return self

    def add_profit_margin(self):
        """Calcule la marge de profit globale par lot annuel (Macro) suite aux retours du tuteur."""
        if "profit" in self.df.columns and "sales" in self.df.columns and "order_date" in self.df.columns:
            # Crée temporairement une colonne d'année si add_date_features n'a pas été appelée avant
            if "order_year" not in self.df.columns:
                self.df["order_year"] = pd.to_datetime(self.df["order_date"]).dt.year
            
            # Calcul de la vraie marge par lot annuel : Somme(profit) / Somme(sales)
            annual_margins = self.df.groupby("order_year").apply(
                lambda chunk: float(chunk["profit"].sum() / chunk["sales"].sum()) if chunk["sales"].sum() != 0 else 0.0
            ).reset_index(name="profit_margin")
            
            # Suppression de l'ancienne colonne si elle existe pour éviter les conflits lors du merge
            if "profit_margin" in self.df.columns:
                self.df.drop(columns=["profit_margin"], inplace=True)
                
            # Fusion de la marge annuelle calculée par lot
            self.df = self.df.merge(annual_margins, on="order_year", how="left")
            
            # Sécurité anti-valeurs aberrantes
            self.df["profit_margin"] = self.df["profit_margin"].replace([float("inf"), -float("inf")], 0)
            self.df["profit_margin"] = self.df["profit_margin"].fillna(0)
            
        elif "profit" in self.df.columns and "sales" in self.df.columns:
            # Fallback historique ligne par ligne si order_date est totalement absente
            self.df["profit_margin"] = self.df["profit"] / self.df["sales"]
            self.df["profit_margin"] = self.df["profit_margin"].replace([float("inf"), -float("inf")], 0).fillna(0)

        return self

    def add_chatbot_context(self):
        # Ajout de 'customer_name' en tout début de liste pour que le test unitaire valide la présence du client !
        columns_for_context = [
            "customer_name",
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