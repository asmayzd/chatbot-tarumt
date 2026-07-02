import kagglehub
import os
import pandas as pd

# Télécharger le dataset
path = kagglehub.dataset_download("fatihilhan/global-superstore-dataset")

print("Path to dataset files:", path)
print("Fichiers disponibles :", os.listdir(path))

# Remplace le nom du fichier si besoin après avoir vu os.listdir(path)
csv_path = os.path.join(path, "Global Superstore.csv")

# Charger les données
df = pd.read_csv(csv_path, encoding="latin1")

# Afficher un aperçu
print(df.head())
print(df.columns)
print(df.shape)