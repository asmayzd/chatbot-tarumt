"""
Génération d'un dataset e-commerce synthétique mais réaliste.
Produit data/raw/ventes_raw.csv (avec quelques valeurs manquantes / anomalies)
et data/processed/dataset_clean.csv (nettoyé, prêt pour le chatbot).

Lancer :  python data/generate_dataset.py
"""
import os
import random
import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "raw", "ventes_raw.csv")
CLEAN = os.path.join(BASE, "processed", "dataset_clean.csv")

# --- Catalogue produits -----------------------------------------------------
PRODUITS = {
    "Smartphone Galaxy S": ("Electronique", 799),
    "Casque Bluetooth Pro": ("Electronique", 129),
    "Ordinateur portable UltraBook": ("Electronique", 1099),
    "Montre connectee FitWatch": ("Electronique", 199),
    "Enceinte SoundBox": ("Electronique", 89),
    "T-shirt coton bio": ("Mode", 25),
    "Jean slim": ("Mode", 59),
    "Baskets running AirLite": ("Mode", 89),
    "Veste impermeable": ("Mode", 79),
    "Cafetiere expresso": ("Maison", 149),
    "Aspirateur robot CleanBot": ("Maison", 299),
    "Set de couteaux ChefPro": ("Maison", 69),
    "Lampe LED design": ("Maison", 39),
    "Livre - Data Science": ("Culture", 35),
    "Casse-tete 1000 pieces": ("Culture", 19),
    "Creme hydratante": ("Beaute", 22),
    "Parfum Eau Fraiche": ("Beaute", 55),
}

REGIONS = ["Ile-de-France", "Auvergne-Rhone-Alpes", "Occitanie",
           "Nouvelle-Aquitaine", "Hauts-de-France", "Bretagne", "PACA"]
CANAUX = ["Web", "Mobile", "Magasin"]
PAIEMENTS = ["Carte", "PayPal", "Virement", "Cheque cadeau"]

# --- Base clients -----------------------------------------------------------
N_CLIENTS = 400
clients = [f"CLI{str(i).zfill(4)}" for i in range(1, N_CLIENTS + 1)]
# Certains clients sont "inactifs" : ils n'achetent que sur le debut de periode
clients_inactifs = set(random.sample(clients, 60))

# --- Generation des commandes ----------------------------------------------
lignes = []
order_id = 100000
start = pd.Timestamp("2025-01-01")
end = pd.Timestamp("2025-12-31")
jours = (end - start).days

# saisonnalite : pic en novembre/decembre (fetes)
def poids_mois(m):
    return {1: 0.7, 2: 0.7, 3: 0.9, 4: 1.0, 5: 1.0, 6: 1.1,
            7: 1.2, 8: 0.9, 9: 1.0, 10: 1.1, 11: 1.6, 12: 1.8}[m]

for _ in range(6000):
    order_id += 1
    d = start + pd.Timedelta(days=int(np.random.randint(0, jours + 1)))
    # sur-echantillonnage des mois de forte activite
    if random.random() > poids_mois(d.month) / 1.8:
        continue
    client = random.choice(clients)
    # les clients inactifs n'achetent que sur janvier-fevrier
    if client in clients_inactifs and d.month > 2:
        continue
    produit = random.choice(list(PRODUITS.keys()))
    categorie, prix_u = PRODUITS[produit]
    qte = int(np.random.choice([1, 1, 1, 2, 2, 3], p=[0.45, 0.2, 0.1, 0.12, 0.08, 0.05]))
    remise = float(np.random.choice([0, 0, 0, 0.1, 0.2], p=[0.6, 0.15, 0.1, 0.1, 0.05]))
    montant = round(prix_u * qte * (1 - remise), 2)
    lignes.append({
        "id_commande": order_id,
        "date": d.strftime("%Y-%m-%d"),
        "id_client": client,
        "produit": produit,
        "categorie": categorie,
        "quantite": qte,
        "prix_unitaire": prix_u,
        "remise": remise,
        "montant": montant,
        "region": random.choice(REGIONS),
        "canal": random.choice(CANAUX),
        "moyen_paiement": random.choice(PAIEMENTS),
    })

df = pd.DataFrame(lignes)

# --- Injection d'anomalies + valeurs manquantes (pour la version RAW) -------
raw = df.copy()
# 1) quelques montants aberrants (erreurs de saisie)
idx = raw.sample(15, random_state=1).index
raw.loc[idx, "montant"] = raw.loc[idx, "montant"] * random.choice([10, 20])
# 2) quantites negatives (retours mal encodes)
idx2 = raw.sample(10, random_state=2).index
raw.loc[idx2, "quantite"] = -raw.loc[idx2, "quantite"]
# 3) valeurs manquantes sur region / moyen_paiement
idx3 = raw.sample(40, random_state=3).index
raw.loc[idx3, "region"] = np.nan
idx4 = raw.sample(25, random_state=4).index
raw.loc[idx4, "moyen_paiement"] = np.nan
# 4) doublons
raw = pd.concat([raw, raw.sample(20, random_state=5)], ignore_index=True)

os.makedirs(os.path.dirname(RAW), exist_ok=True)
raw.to_csv(RAW, index=False)

# --- Nettoyage -> dataset_clean --------------------------------------------
clean = raw.copy()
clean = clean.drop_duplicates(subset="id_commande")
clean = clean[clean["quantite"] > 0]                       # retire quantites <= 0
# recalcule montant coherent pour retirer les aberrations
clean["montant"] = (clean["prix_unitaire"] * clean["quantite"] *
                    (1 - clean["remise"])).round(2)
clean["region"] = clean["region"].fillna("Non renseigne")
clean["moyen_paiement"] = clean["moyen_paiement"].fillna("Inconnu")
clean["date"] = pd.to_datetime(clean["date"])
clean["mois"] = clean["date"].dt.to_period("M").astype(str)
clean = clean.sort_values("date").reset_index(drop=True)

# On laisse volontairement une poignee d'anomalies "residuelles" (12 commandes)
# que le nettoyage n'a pas attrapees : montant incoherent vs prix*quantite.
# Objectif pedagogique : que le module de detection d'anomalies ait de quoi trouver.
ano_idx = clean.sample(12, random_state=7).index
clean.loc[ano_idx, "montant"] = (clean.loc[ano_idx, "montant"] * 6).round(2)

os.makedirs(os.path.dirname(CLEAN), exist_ok=True)
clean.to_csv(CLEAN, index=False)

print(f"RAW   : {len(raw)} lignes -> {RAW}")
print(f"CLEAN : {len(clean)} lignes -> {CLEAN}")
print(f"CA total : {clean['montant'].sum():,.2f} EUR")
print(f"Clients uniques : {clean['id_client'].nunique()}")
print(f"Periode : {clean['date'].min().date()} -> {clean['date'].max().date()}")
