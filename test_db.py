import sqlite3

conn = sqlite3.connect("data/superstore_bi.db")
cursor = conn.cursor()

# 1. Lister toutes les tables créées dans la base
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("📊 Tables trouvées dans la base de données :")
for table in tables:
    print(f"  - {table[0]}")

print("\n📐 Structure DDL vérifiée pour la table 'orders' :")
# 2. Afficher le DDL exact stocké par SQLite pour valider les PK/FK
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='orders';")
ddl = cursor.fetchone()
if ddl:
    print(ddl[0])

cursor.execute("SELECT COUNT(*) FROM order_items;")
print(f"🔢 Nombre total de lignes d'articles insérées : {cursor.fetchone()[0]}")
conn.close()