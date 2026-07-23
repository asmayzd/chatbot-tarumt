import sys
import os

# Ajoute la racine du projet au chemin de recherche Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pandas as pd
from src.data_science.data_loader import DataLoader
from src.data_science.data_cleaner import DataCleaner
from src.data_science.feature_engineer import FeatureEngineer
from src.database.db_manager import get_db_connection, init_db

def populate_database():
    init_db()
    
    print("⏳ Étape 1 : Chargement, nettoyage et ingénierie des données...")
    loader = DataLoader(file_path="data/superstore.csv")
    df_raw = loader.load_csv()
    cleaner = DataCleaner(df_raw)
    df_clean = cleaner.clean()
    
    # 1. Utilisation de ton FeatureEngineer existant pour les autres variables
    engineer = FeatureEngineer(df_clean)
    df = engineer.transform()
    
    # 2. LOGIQUE DE CALCUL PAR ANNEE (Demande du prof) :
    # On extrait l'année pour pouvoir grouper les données
    df['order_year'] = pd.to_datetime(df['order_date']).dt.year
    
    # On calcule la vraie marge globale par lot annuel : SOMME(profit) / SOMME(sales)
    annual_margins = df.groupby('order_year').apply(
        lambda x: float(x['profit'].sum() / x['sales'].sum()) if x['sales'].sum() != 0 else 0.0
    ).reset_index(name='annual_profit_margin')
    
    # On fusionne (JOIN) cette marge annuelle directement dans notre DataFrame global
    df = df.merge(annual_margins, on='order_year', how='left')
    
    print(f"✅ {len(df)} lignes enrichies par lot annuel et prêtes à être migrées.")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    chunk_size = 5000  # Taille des lots pour l'ingestion de toutes les tables
    
    try:
        # ---- Étape 2 : Table CUSTOMERS ----
        print("📥 Insertion dans la table 'customers' par lots...")
        df_customers = df[['customer_id', 'customer_name', 'segment']].drop_duplicates(subset=['customer_id'])
        customer_tuples = [tuple(x) for x in df_customers.values]
        
        for i in range(0, len(customer_tuples), chunk_size):
            cursor.executemany("""
                INSERT INTO customers (customer_id, customer_name, segment)
                VALUES (%s, %s, %s)
                ON CONFLICT (customer_id) DO NOTHING
            """, customer_tuples[i:i + chunk_size])
            
        # ---- Étape 3 : Table PRODUCTS ----
        print("📥 Insertion dans la table 'products' par lots...")
        df_products = df[['product_id', 'product_name', 'category', 'sub_category']].drop_duplicates(subset=['product_id'])
        product_tuples = [tuple(x) for x in df_products.values]
        
        for i in range(0, len(product_tuples), chunk_size):
            cursor.executemany("""
                INSERT INTO products (product_id, product_name, category, sub_category)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (product_id) DO NOTHING
            """, product_tuples[i:i + chunk_size])

        # ---- Étape 4 : Table ORDERS ----
        print("📥 Insertion dans la table 'orders' par lots...")
        df_orders = df[[
            'order_id', 'customer_id', 'order_date', 'ship_date', 
            'ship_mode', 'market', 'region', 'country', 'city', 'state'
        ]].drop_duplicates(subset=['order_id'])
        
        order_tuples = [
            (
                row['order_id'], row['customer_id'], 
                str(row['order_date']), str(row['ship_date']), 
                row['ship_mode'], row['market'], row['region'], row['country'], row['city'], row['state']
            )
            for _, row in df_orders.iterrows()
        ]
        
        for i in range(0, len(order_tuples), chunk_size):
            cursor.executemany("""
                INSERT INTO orders (order_id, customer_id, order_date, ship_date, ship_mode, market, region, country, city, state)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (order_id) DO NOTHING
            """, order_tuples[i:i + chunk_size])

        # ---- Étape 5 : Table ORDER_ITEMS (Par lots / Chunks) ----
        print("📥 Insertion dans la table 'order_items' par lots...")
        for i in range(0, len(df), chunk_size):
            df_chunk = df.iloc[i:i + chunk_size]
            
            item_tuples = [
                (
                    row['order_id'], 
                    row['product_id'], 
                    float(row['sales']), 
                    int(row['quantity']), 
                    float(row['discount']), 
                    float(row['profit']), 
                    float(row['shipping_cost']), 
                    row['order_priority'],
                    int(row['shipping_delay_days']),   
                    float(row['annual_profit_margin']),
                    str(row['chatbot_context'])        
                )
                for _, row in df_chunk.iterrows()
            ]
            
            cursor.executemany("""
                INSERT INTO order_items (
                    order_id, product_id, sales, quantity, discount, profit, 
                    shipping_cost, order_priority, shipping_delay_days, profit_margin, chatbot_context
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, item_tuples)
            
        # ---- Étape 6 : Table relationnelle intermédiaire CUSTOMER_MESSAGES (Many-to-Many) ----
        # Placé en dehors de la boucle principale pour s'exécuter une seule fois au niveau macro
        print("📥 Initialisation des liaisons Many-to-Many dans 'customer_messages'...")
        sample_customer = customer_tuples[0][0] if customer_tuples else None
        
        if sample_customer:
            # 1. Création d'une session de chat test
            cursor.execute("""
                INSERT INTO chat_sessions (student_id, session_name) 
                VALUES ('SYSTEM_ING2', 'Initial Architecture Setup') RETURNING session_id;
            """)
            session_id = cursor.fetchone()[0]
            
            # 2. Création d'un message test lié à cette session
            cursor.execute("""
                INSERT INTO chat_messages (session_id, role, content) 
                VALUES (%s, 'user', 'Hello PostgreSQL Superstore!') RETURNING message_id;
            """, (session_id,))
            message_id = cursor.fetchone()[0]
            
            # 3. Insertion dans la table de jointure Many-to-Many
            cursor.execute("""
                INSERT INTO customer_messages (customer_id, message_id) 
                VALUES (%s, %s)
                ON CONFLICT (customer_id, message_id) DO NOTHING;
            """, (sample_customer, message_id))

        conn.commit()
        print("🎉 Succès ! L'ingestion par lots (avec marges calculées par année) fonctionne parfaitement sur PostgreSQL.")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur lors de l'ingestion : {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    populate_database()