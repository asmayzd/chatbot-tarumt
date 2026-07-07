import sys
import os

# Ajoute la racine du projet au chemin de recherche Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import pandas as pd
from src.database.db_manager import get_db_connection
from src.data_science.data_loader import DataLoader
from src.data_science.data_cleaner import DataCleaner

def populate_database():
    print("⏳ Étape 1 : Chargement et nettoyage du fichier CSV lourd...")
    # 1. Utilisation de tes outils de Data Science existants
    loader = DataLoader(file_path="data/superstore.csv")
    df_raw = loader.load_csv()
    cleaner = DataCleaner(df_raw)
    df = cleaner.clean()
    
    print(f"✅ {len(df)} lignes prêtes à être migrées.")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Étape 2 : Table CUSTOMERS (Extraction des clients uniques)
        print("📥 Insertion dans la table 'customers'...")
        df_customers = df[['customer_id', 'customer_name', 'segment']].drop_duplicates(subset=['customer_id'])
        for _, row in df_customers.iterrows():
            cursor.execute("""
                INSERT OR IGNORE INTO customers (customer_id, customer_name, segment)
                VALUES (?, ?, ?)
            """, (row['customer_id'], row['customer_name'], row['segment']))
            
        # Étape 3 : Table PRODUCTS (Extraction des produits uniques)
        print("📥 Insertion dans la table 'products'...")
        df_products = df[['product_id', 'product_name', 'category', 'sub_category']].drop_duplicates(subset=['product_id'])
        for _, row in df_products.iterrows():
            cursor.execute("""
                INSERT OR IGNORE INTO products (product_id, product_name, category, sub_category)
                VALUES (?, ?, ?, ?)
            """, (row['product_id'], row['product_name'], row['category'], row['sub_category']))

        # Étape 4 : Table ORDERS (Extraction des commandes uniques)
        print("📥 Insertion dans la table 'orders'...")
        df_orders = df[[
            'order_id', 'customer_id', 'order_date', 'ship_date', 
            'ship_mode', 'market', 'region', 'country', 'city', 'state'
        ]].drop_duplicates(subset=['order_id'])
        
        for _, row in df_orders.iterrows():
            cursor.execute("""
                INSERT OR IGNORE INTO orders (order_id, customer_id, order_date, ship_date, ship_mode, market, region, country, city, state)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['order_id'], row['customer_id'], 
                str(row['order_date']), str(row['ship_date']), # Conversion des dates en chaînes pour SQLite
                row['ship_mode'], row['market'], row['region'], row['country'], row['city'], row['state']
            ))

        # Étape 5 : Table ORDER_ITEMS (Insertion de toutes les lignes de vente d'articles)
        print("📥 Insertion dans la table 'order_items'...")
        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, sales, quantity, discount, profit, shipping_cost, order_priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['order_id'], row['product_id'], float(row['sales']), 
                int(row['quantity']), float(row['discount']), float(row['profit']), 
                float(row['shipping_cost']), row['order_priority']
            ))
            
        conn.commit()
        print("🎉 Magnifique Asma ! La base de données Superstore est maintenant remplie et 100% opérationnelle en 3NF.")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur lors de l'ingestion : {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    populate_database()