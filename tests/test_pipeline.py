import sys
import os
import unittest
import pandas as pd

# Ajoute la racine au chemin de recherche
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_science.data_cleaner import DataCleaner
from src.data_science.feature_engineer import FeatureEngineer

class TestSuperstorePipeline(unittest.TestCase):

    def setUp(self):
        """Prépare un petit DataFrame de test avec des données fictives brutes."""
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

    def test_shipping_delay_calculation(self):
        """Vérifie si le calcul du délai de livraison (Feature Engineering) est exact."""
        engineer = FeatureEngineer(self.mock_data)
        df_result = engineer.transform()
        
        # Ligne 1 : 2026-07-05 - 2026-07-01 = 4 jours
        self.assertEqual(df_result.loc[0, "shipping_delay_days"], 4)
        # Ligne 2 : 2026-07-02 - 2026-07-01 = 1 jour
        self.assertEqual(df_result.loc[1, "shipping_delay_days"], 1)

    def test_profit_margin_calculation(self):
        """Vérifie si la marge de profit est correctement calculée."""
        engineer = FeatureEngineer(self.mock_data)
        df_result = engineer.transform()
        
        # Ligne 1 : Profit(20) / Sales(100) = 0.2 (20%)
        self.assertAlmostEqual(df_result.loc[0, "profit_margin"], 0.2)
        # Ligne 2 : Profit(-10) / Sales(50) = -0.2 (-20%)
        self.assertAlmostEqual(df_result.loc[1, "profit_margin"], -0.2)

    def test_chatbot_context_creation(self):
        """Vérifie que la chaîne de contexte concaténée n'est pas vide."""
        engineer = FeatureEngineer(self.mock_data)
        df_result = engineer.transform()
        
        self.assertIn("chatbot_context", df_result.columns)
        self.assertTrue(df_result["chatbot_context"].str.contains("Asma|Office Supplies").any())

if __name__ == "__main__":
    unittest.main()