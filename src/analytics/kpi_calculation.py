"""
Module BI & Analytics — Calcul des KPI métier.

Contrat exposé au reste de l'application :
    get_kpi(metric_name: str) -> dict

Le chatbot (module ML) appelle get_kpi() pour répondre aux questions métier.
Le dashboard (dashboard.py) réutilise les mêmes fonctions.
"""
import os
import functools
import pandas as pd

DATA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "data", "processed", "dataset_clean.csv",
)


@functools.lru_cache(maxsize=1)
def load_data() -> pd.DataFrame:
    """Charge le dataset nettoyé (mis en cache)."""
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    df["mois"] = df["date"].dt.to_period("M").astype(str)
    return df


# --- KPI unitaires ----------------------------------------------------------
def chiffre_affaires_total() -> float:
    return round(load_data()["montant"].sum(), 2)

def nombre_commandes() -> int:
    return int(load_data()["id_commande"].nunique())

def panier_moyen() -> float:
    df = load_data()
    return round(df["montant"].sum() / df["id_commande"].nunique(), 2)

def clients_actifs() -> int:
    return int(load_data()["id_client"].nunique())

def produits_populaires(n: int = 5) -> pd.DataFrame:
    df = load_data()
    return (df.groupby("produit")["quantite"].sum()
              .sort_values(ascending=False).head(n).reset_index()
              .rename(columns={"quantite": "unites_vendues"}))

def ca_par_mois() -> pd.DataFrame:
    df = load_data()
    return (df.groupby("mois")["montant"].sum().round(2)
              .reset_index().rename(columns={"montant": "ca"}))

def meilleur_mois() -> dict:
    m = ca_par_mois().sort_values("ca", ascending=False).iloc[0]
    return {"mois": m["mois"], "ca": round(float(m["ca"]), 2)}

def ca_par_categorie() -> pd.DataFrame:
    df = load_data()
    return (df.groupby("categorie")["montant"].sum().round(2)
              .sort_values(ascending=False).reset_index()
              .rename(columns={"montant": "ca"}))

def ca_par_region() -> pd.DataFrame:
    df = load_data()
    return (df.groupby("region")["montant"].sum().round(2)
              .sort_values(ascending=False).reset_index()
              .rename(columns={"montant": "ca"}))

def clients_inactifs(seuil_mois: str = "2025-03") -> pd.DataFrame:
    """Clients dont le dernier achat est antérieur au seuil (par défaut mars 2025)."""
    df = load_data()
    dernier_achat = df.groupby("id_client")["date"].max().reset_index()
    seuil = pd.Timestamp(seuil_mois + "-01")
    inactifs = dernier_achat[dernier_achat["date"] < seuil].copy()
    inactifs["dernier_achat"] = inactifs["date"].dt.date
    return inactifs[["id_client", "dernier_achat"]].sort_values("dernier_achat")

def fiche_clients(n: int = 10) -> pd.DataFrame:
    """Vue 360 par client (donnée sensible : réservée aux rôles autorisés)."""
    df = load_data()
    agg = (df.groupby("id_client")
             .agg(nb_commandes=("id_commande", "nunique"),
                  ca=("montant", "sum"),
                  dernier_achat=("date", "max"))
             .reset_index()
             .sort_values("ca", ascending=False))
    agg["ca"] = agg["ca"].round(2)
    agg["dernier_achat"] = agg["dernier_achat"].dt.date
    return agg.head(n)


def detecter_anomalies() -> pd.DataFrame:
    """
    Détection d'anomalies sur le PRIX UNITAIRE EFFECTIF (montant / quantité).
    Pour une commande normale, ce ratio vaut prix_unitaire * (1 - remise),
    donc il reste proche du prix catalogue quelle que soit la quantité.
    Une commande est signalée si l'écart au prix catalogue dépasse 50 %
    (au-dessus) : cela isole les montants incohérents sans flaguer les
    grosses quantités.
    """
    df = load_data().copy()
    df["prix_effectif"] = df["montant"] / df["quantite"]
    # écart relatif au prix catalogue
    df["ecart"] = (df["prix_effectif"] - df["prix_unitaire"]) / df["prix_unitaire"]
    anomalies = df[df["ecart"] > 0.5].copy()      # prix effectif > 150 % du catalogue
    anomalies["ecart_pct"] = (anomalies["ecart"] * 100).round(0)
    return anomalies[["id_commande", "date", "produit", "quantite",
                      "prix_unitaire", "montant", "ecart_pct"]] \
        .sort_values("montant", ascending=False)


# --- Contrat principal ------------------------------------------------------
def get_kpi(metric_name: str) -> dict:
    """
    Retourne un KPI sous forme normalisée.
    Contrat : { "metric": str, "value": ..., "detail": ..., "period": str }

    metric_name accepté :
      total_revenue, orders_count, average_basket, active_customers,
      top_products, best_month, revenue_by_month, revenue_by_category,
      revenue_by_region, inactive_customers, anomalies
    """
    df = load_data()
    periode = f"{df['date'].min().date()} -> {df['date'].max().date()}"
    m = (metric_name or "").strip().lower()

    if m in ("total_revenue", "ca_total", "chiffre_affaires"):
        return {"metric": "total_revenue", "value": chiffre_affaires_total(),
                "detail": None, "period": periode, "unit": "EUR"}

    if m in ("orders_count", "nb_commandes"):
        return {"metric": "orders_count", "value": nombre_commandes(),
                "detail": None, "period": periode, "unit": "commandes"}

    if m in ("average_basket", "panier_moyen"):
        return {"metric": "average_basket", "value": panier_moyen(),
                "detail": None, "period": periode, "unit": "EUR"}

    if m in ("active_customers", "clients_actifs"):
        return {"metric": "active_customers", "value": clients_actifs(),
                "detail": None, "period": periode, "unit": "clients"}

    if m in ("top_products", "produits_populaires"):
        top = produits_populaires()
        return {"metric": "top_products", "value": top.iloc[0]["produit"],
                "detail": top.to_dict(orient="records"),
                "period": periode, "unit": None}

    if m in ("best_month", "meilleur_mois"):
        mm = meilleur_mois()
        return {"metric": "best_month", "value": mm["mois"],
                "detail": mm, "period": periode, "unit": None}

    if m in ("revenue_by_month", "ca_par_mois"):
        return {"metric": "revenue_by_month", "value": None,
                "detail": ca_par_mois().to_dict(orient="records"),
                "period": periode, "unit": "EUR"}

    if m in ("revenue_by_category", "ca_par_categorie"):
        cat = ca_par_categorie()
        return {"metric": "revenue_by_category", "value": cat.iloc[0]["categorie"],
                "detail": cat.to_dict(orient="records"),
                "period": periode, "unit": "EUR"}

    if m in ("revenue_by_region", "ca_par_region"):
        reg = ca_par_region()
        return {"metric": "revenue_by_region", "value": reg.iloc[0]["region"],
                "detail": reg.to_dict(orient="records"),
                "period": periode, "unit": "EUR"}

    if m in ("inactive_customers", "clients_inactifs"):
        inact = clients_inactifs()
        return {"metric": "inactive_customers", "value": len(inact),
                "detail": inact.head(20).to_dict(orient="records"),
                "period": periode, "unit": "clients"}

    if m in ("anomalies", "anomalie"):
        ano = detecter_anomalies()
        return {"metric": "anomalies", "value": len(ano),
                "detail": ano.head(20).astype(str).to_dict(orient="records"),
                "period": periode, "unit": "commandes"}

    return {"metric": metric_name, "value": None,
            "detail": "KPI inconnu", "period": periode, "unit": None,
            "error": True}


if __name__ == "__main__":
    for k in ["total_revenue", "top_products", "best_month",
              "inactive_customers", "anomalies", "revenue_by_category"]:
        r = get_kpi(k)
        print(f"{k:22s} -> value={r['value']}  ({r.get('unit')})")
