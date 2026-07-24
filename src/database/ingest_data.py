import os
import pandas as pd
from psycopg2.extras import execute_values
from src.database.db_manager import get_db_connection, init_db

def populate_database():
    """Charge le CSV local et peuple Supabase en quelques secondes grâce à execute_values."""
    init_db()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SET statement_timeout = 0;")
        conn.commit()

        csv_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "superstore.csv")
        if not os.path.exists(csv_path):
            csv_path = "data/superstore.csv"

        print("⏳ Étape 1 : Chargement express du fichier CSV...")
        
        try:
            df = pd.read_csv(csv_path, encoding="latin1")
        except Exception:
            df = pd.read_csv(csv_path, encoding="utf-8", errors="ignore")

        df.columns = df.columns.str.strip()

        # Mapping des colonnes du CSV
        cid_col, cname_col, seg_col = 'Customer.ID', 'Customer.Name', 'Segment'
        pid_col, pname_col, cat_col, sub_col = 'Product.ID', 'Product.Name', 'Category', 'Sub.Category'
        oid_col, odate_col, sdate_col, smode_col = 'Order.ID', 'Order.Date', 'Ship.Date', 'Ship.Mode'
        
        # Champs localisation pour orders
        mkt_col = 'Market' if 'Market' in df.columns else None
        reg_col = 'Region' if 'Region' in df.columns else None
        ctr_col = 'Country' if 'Country' in df.columns else None
        cty_col = 'City' if 'City' in df.columns else None
        sta_col = 'State' if 'State' in df.columns else None

        sales_col, qty_col, disc_col, prof_col = 'Sales', 'Quantity', 'Discount', 'Profit'
        ship_cost_col = 'Shipping.Cost' if 'Shipping.Cost' in df.columns else 'shipping_cost'
        prio_col = 'Order.Priority' if 'Order.Priority' in df.columns else 'order_priority'

        if ship_cost_col not in df.columns:
            df[ship_cost_col] = 0.0
        if prio_col not in df.columns:
            df[prio_col] = 'Medium'

        # Remplissage par défaut des colonnes géo si absentes
        for col, default_val in [(mkt_col, 'APAC'), (reg_col, 'Unknown'), (ctr_col, 'Unknown'), (cty_col, 'Unknown'), (sta_col, 'Unknown')]:
            if col not in df.columns or col is None:
                df[col if col else 'tmp_col'] = default_val

        mkt_col = mkt_col if mkt_col in df.columns else 'tmp_col'
        reg_col = reg_col if reg_col in df.columns else 'tmp_col'
        ctr_col = ctr_col if ctr_col in df.columns else 'tmp_col'
        cty_col = cty_col if cty_col in df.columns else 'tmp_col'
        sta_col = sta_col if sta_col in df.columns else 'tmp_col'

        # DataFrames
        customers_df = df[[cid_col, cname_col, seg_col]].drop_duplicates()
        products_df  = df[[pid_col, pname_col, cat_col, sub_col]].drop_duplicates(subset=[pid_col])
        orders_df    = df[[oid_col, cid_col, odate_col, sdate_col, smode_col, mkt_col, reg_col, ctr_col, cty_col, sta_col]].drop_duplicates(subset=[oid_col])
        
        # Order Items incluant Shipping Cost & Order Priority
        order_items_df = df[[oid_col, pid_col, sales_col, qty_col, disc_col, prof_col, ship_cost_col, prio_col]]

        # Nettoyage et conversion des dates
        orders_df[odate_col] = pd.to_datetime(orders_df[odate_col], format='mixed', dayfirst=False, errors='coerce').dt.strftime('%Y-%m-%d')
        orders_df[sdate_col] = pd.to_datetime(orders_df[sdate_col], format='mixed', dayfirst=False, errors='coerce').dt.strftime('%Y-%m-%d')

        print("⚡ Étape 2 : Injection Turbo vers Supabase...")

        # 1. Customers
        print("  └─ Injection Customers...")
        cust_tuples = [tuple(x) for x in customers_df.to_numpy()]
        execute_values(cursor, "INSERT INTO customers (customer_id, customer_name, segment) VALUES %s ON CONFLICT (customer_id) DO NOTHING;", cust_tuples, page_size=2000)
        conn.commit()

        # 2. Products
        print("  └─ Injection Products...")
        prod_tuples = [tuple(x) for x in products_df.to_numpy()]
        execute_values(cursor, "INSERT INTO products (product_id, product_name, category, sub_category) VALUES %s ON CONFLICT (product_id) DO NOTHING;", prod_tuples, page_size=2000)
        conn.commit()

        # 3. Orders
        print("  └─ Injection Orders...")
        ord_tuples = [tuple(x) for x in orders_df.to_numpy()]
        execute_values(
            cursor, 
            "INSERT INTO orders (order_id, customer_id, order_date, ship_date, ship_mode, market, region, country, city, state) VALUES %s ON CONFLICT (order_id) DO NOTHING;", 
            ord_tuples, 
            page_size=2000
        )
        conn.commit()

        # 4. Order Items (50,000+ lignes)
        print("  └─ Injection Order Items...")
        items_tuples = [tuple(x) for x in order_items_df.to_numpy()]
        execute_values(
            cursor, 
            "INSERT INTO order_items (order_id, product_id, sales, quantity, discount, profit, shipping_cost, order_priority) VALUES %s;", 
            items_tuples, 
            page_size=5000
        )
        conn.commit()

        print("\n🚀 MIGRATION RÉUSSIE EN QUELQUES SECONDES !")

    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur : {str(e)}")
        raise e
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    populate_database()