import sys
import os
import unittest
import pandas as pd

# Ajoute la racine au chemin de recherche
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_science.feature_engineer import FeatureEngineer

class TestBaseSetup(unittest.TestCase):
    """Classe de base fournissant un jeu de données standardisé pour les tests individuels."""
    def setUp(self):
        self.mock_data = pd.DataFrame({
            "order_id": ["CA-2026-1001", "CA-2026-1002"],
            "customer_id": ["AA-101", "BB-102"],
            "customer_name": ["Asma", "Besma"],
            "segment": ["Consumer", "Corporate"],
            "product_id": ["OFF-FA-1000", "TEC-AC-2000"],
            "product_name": ["Surligneurs", "Clavier Sans Fil"],
            "category": ["Office Supplies", "Technology"],
            "sub_category": ["Fasteners", "Accessories"],
            "order_date": [pd.Timestamp("2026-07-01"), pd.Timestamp("2026-07-01")],
            "ship_date": [pd.Timestamp("2026-07-05"), pd.Timestamp("2026-07-02")],
            "ship_mode": ["Standard Class", "Second Class"],
            "market": ["US", "EU"],
            "region": ["West", "Central"],
            "country": ["United States", "France"],
            "city": ["Los Angeles", "Paris"],
            "state": ["California", "Île-de-France"],
            "sales": [100.0, 50.0],
            "quantity": [2, 1],
            "discount": [0.0, 0.1],
            "profit": [20.0, -10.0],
            "shipping_cost": [5.5, 2.1],
            "order_priority": ["Medium", "High"]
        })


class TestShippingDelayCalculation(TestBaseSetup):
    """Série de tests isolés focalisés uniquement sur les calculs de délais logistiques."""

    def test_shipping_delay_for_standard_delivery(self):
        """Vérifie le calcul d'un délai standard (ex: 4 jours d'écart)"""
        engineer = FeatureEngineer(self.mock_data)
        df_result = engineer.transform()
        self.assertEqual(df_result.loc[0, "shipping_delay_days"], 4)

    def test_shipping_delay_for_express_delivery(self):
        """Vérifie le calcul d'un délai court (ex: 1 jour d'écart)"""
        engineer = FeatureEngineer(self.mock_data)
        df_result = engineer.transform()
        self.assertEqual(df_result.loc[1, "shipping_delay_days"], 1)

    def test_shipping_delay_during_leap_years(self):
        """Vérifie que le calcul gère proprement les franchissements délicats (ex: Février 2024 bissextile)"""
        leap_data = self.mock_data.copy()
        leap_data.loc[0, "order_date"] = pd.Timestamp("2024-02-28")
        leap_data.loc[0, "ship_date"] = pd.Timestamp("2024-03-01")
        
        engineer = FeatureEngineer(leap_data)
        df_result = engineer.transform()
        # 2024 étant bissextile, le 29 février existe -> Écart de 2 jours
        self.assertEqual(df_result.loc[0, "shipping_delay_days"], 2)


class TestAnnualProfitMarginLogic(TestBaseSetup):
    """Série de tests validant la nouvelle logique macro par lot annuel (Retour réunion tuteur)."""

    def test_profit_margin_is_identical_for_same_year(self):
        """Vérifie que deux lignes de la même année héritent strictement de la même marge annuelle globale."""
        # Somme Profit = 20 + (-10) = 10 | Somme Sales = 100 + 50 = 150
        # Marge globale attendue pour 2026 = 10 / 150 = 0.06666...
        engineer = FeatureEngineer(self.mock_data)
        df_result = engineer.transform()
        
        margin_line_1 = df_result.loc[0, "profit_margin"]
        margin_line_2 = df_result.loc[1, "profit_margin"]
        
        # Les deux lignes de 2026 doivent avoir la même valeur agrégée
        self.assertAlmostEqual(margin_line_1, margin_line_2, places=4)

    def test_profit_margin_value_accuracy(self):
        """Vérifie la justesse mathématique du calcul macro (Somme des Profits / Somme des Ventes)."""
        engineer = FeatureEngineer(self.mock_data)
        df_result = engineer.transform()
        
        expected_macro_margin = 10.0 / 150.0
        self.assertAlmostEqual(df_result.loc[0, "profit_margin"], expected_macro_margin, places=5)

    def test_profit_margin_handling_zero_sales(self):
        """Vérifie que le pipeline évite la division par zéro si un lot annuel n'a aucune vente enregistrée."""
        zero_sales_data = self.mock_data.copy()
        zero_sales_data["sales"] = [0.0, 0.0]
        zero_sales_data["profit"] = [0.0, 0.0]
        
        engineer = FeatureEngineer(zero_sales_data)
        df_result = engineer.transform()
        
        # Le code doit renvoyer une marge par défaut de 0.0 sans faire planter le script
        self.assertEqual(df_result.loc[0, "profit_margin"], 0.0)


class TestChatbotContextGeneration(TestBaseSetup):
    """Série de tests isolés focalisés sur la création des métadonnées textuelles pour le LLM."""

    def test_chatbot_context_column_presence(self):
        """S'assure que la colonne requise par l'agent SQL est bien injectée dans le schéma final."""
        engineer = FeatureEngineer(self.mock_data)
        df_result = engineer.transform()
        self.assertIn("chatbot_context", df_result.columns)

    def test_chatbot_context_content_contains_customer_data(self):
        """Vérifie que la chaîne de texte générée capture bien les entités métiers clés (Nom du client)."""
        engineer = FeatureEngineer(self.mock_data)
        df_result = engineer.transform()
        self.assertTrue(df_result.loc[0, "chatbot_context"].__contains__("Asma"))

    def test_chatbot_context_content_contains_product_metadata(self):
        """Vérifie que la chaîne capture également le contexte produit."""
        engineer = FeatureEngineer(self.mock_data)
        df_result = engineer.transform()
        self.assertTrue(df_result.loc[0, "chatbot_context"].__contains__("Office Supplies"))


if __name__ == "__main__":
    unittest.main()