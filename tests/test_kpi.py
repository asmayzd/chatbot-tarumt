"""Tests du module BI (KPI). Lancer : pytest tests/test_kpi.py"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from src.analytics import kpi_calculation as kpi


def test_ca_total_positif():
    assert kpi.chiffre_affaires_total() > 0

def test_get_kpi_total_revenue():
    r = kpi.get_kpi("total_revenue")
    assert r["metric"] == "total_revenue"
    assert isinstance(r["value"], (int, float))
    assert r["value"] > 0

def test_get_kpi_top_products():
    r = kpi.get_kpi("top_products")
    assert r["detail"] and len(r["detail"]) >= 1
    assert "produit" in r["detail"][0]

def test_meilleur_mois_format():
    r = kpi.get_kpi("best_month")
    assert isinstance(r["value"], str)
    assert r["detail"]["ca"] > 0

def test_anomalies_raisonnable():
    r = kpi.get_kpi("anomalies")
    # doit détecter des anomalies mais pas la moitié du dataset
    assert 0 < r["value"] < 100

def test_kpi_inconnu():
    r = kpi.get_kpi("metrique_bidon")
    assert r.get("error") is True
