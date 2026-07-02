"""
Module BI & Analytics — Dashboard.

Fonctions de rendu réutilisées par l'application intégrée (src/app.py).
On sépare la logique de calcul (kpi_calculation) du rendu (ici).

Peut aussi être lancé en standalone :
    streamlit run src/analytics/dashboard.py
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import pandas as pd
import plotly.express as px

from src.analytics import kpi_calculation as kpi


def render_kpi_cards(st):
    """Affiche la rangée de cartes KPI en haut du dashboard."""
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Chiffre d'affaires", f"{kpi.chiffre_affaires_total():,.0f} €")
    c2.metric("Commandes", f"{kpi.nombre_commandes():,}")
    c3.metric("Panier moyen", f"{kpi.panier_moyen():,.2f} €")
    c4.metric("Clients actifs", f"{kpi.clients_actifs():,}")


def render_charts(st):
    """Affiche les graphiques principaux du dashboard."""
    # CA par mois
    ca_mois = kpi.ca_par_mois()
    fig1 = px.line(ca_mois, x="mois", y="ca", markers=True,
                   title="Évolution du chiffre d'affaires par mois")
    fig1.update_layout(xaxis_title="Mois", yaxis_title="CA (€)")
    st.plotly_chart(fig1, use_container_width=True)

    col1, col2 = st.columns(2)

    # Top produits
    top = kpi.produits_populaires(8)
    fig2 = px.bar(top, x="unites_vendues", y="produit", orientation="h",
                  title="Produits les plus vendus (unités)")
    fig2.update_layout(yaxis={"categoryorder": "total ascending"},
                       xaxis_title="Unités vendues", yaxis_title="")
    col1.plotly_chart(fig2, use_container_width=True)

    # CA par catégorie
    cat = kpi.ca_par_categorie()
    fig3 = px.pie(cat, names="categorie", values="ca",
                  title="Répartition du CA par catégorie")
    col2.plotly_chart(fig3, use_container_width=True)

    col3, col4 = st.columns(2)

    # CA par région
    reg = kpi.ca_par_region()
    fig4 = px.bar(reg, x="region", y="ca", title="CA par région")
    fig4.update_layout(xaxis_title="", yaxis_title="CA (€)", xaxis_tickangle=-30)
    col3.plotly_chart(fig4, use_container_width=True)

    # Anomalies
    ano = kpi.detecter_anomalies()
    col4.markdown(f"**Anomalies détectées : {len(ano)}**")
    col4.caption("Commandes dont le prix unitaire effectif dépasse 150 % du catalogue.")
    if len(ano):
        col4.dataframe(ano.head(12), use_container_width=True, hide_index=True)


def render_interactions(st, logs_df: pd.DataFrame):
    """Affiche les analytics d'usage du chatbot à partir des logs."""
    st.subheader("Analytics des interactions chatbot")
    if logs_df is None or logs_df.empty:
        st.info("Aucune interaction enregistrée pour l'instant. "
                "Posez des questions dans l'onglet Chatbot.")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Questions posées", len(logs_df))
    c2.metric("Bloquées (sécurité)", int((~logs_df["autorise"]).sum()))
    if "categorie" in logs_df:
        top_cat = logs_df["categorie"].mode()
        c3.metric("Intention fréquente", top_cat.iloc[0] if len(top_cat) else "-")
    if "categorie" in logs_df:
        rep = logs_df["categorie"].value_counts().reset_index()
        rep.columns = ["categorie", "nombre"]
        fig = px.bar(rep, x="categorie", y="nombre",
                     title="Répartition des questions par intention")
        st.plotly_chart(fig, use_container_width=True)


def render_dashboard(st, logs_df: pd.DataFrame = None):
    """Rendu complet du dashboard (utilisé par app.py)."""
    st.header("📊 Dashboard BI — E-commerce")
    render_kpi_cards(st)
    st.divider()
    render_charts(st)
    st.divider()
    render_interactions(st, logs_df)


# --- Mode standalone --------------------------------------------------------
if __name__ == "__main__":
    import streamlit as st
    st.set_page_config(page_title="Dashboard BI", layout="wide")
    render_dashboard(st)
