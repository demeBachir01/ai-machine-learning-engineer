import pandas as pd
import pytest

from src.utils import (cle_texte, normaliser_type_bien, normaliser_periodicite, normaliser_type_transaction,
                       inferer_type_transaction, construire_index_geo, normaliser_localisation)

GEO = pd.DataFrame({"region": ["Dakar", "Thiès", "Thiès", "Fatick", "Kaolack"],
                    "ville": ["Dakar", "Thiès", "Mbour", "Gossas", "Mbour"]})  # Mbour volontairement ambiguë
INDEX = construire_index_geo(GEO)


@pytest.mark.parametrize("brut,attendu", [("  THIÈS ", "thies"), ("Guédiawaye", "guediawaye"),
                                           ("Saint   Louis", "saint louis"), ("dakar", "dakar")])
def test_cle_texte(brut, attendu):
    assert cle_texte(brut) == attendu


@pytest.mark.parametrize("brut,valeur,statut", [("Villa", "Villa", "ok"), ("appart", "Appartement", "corrige"),
                                                 ("STUDIO", "Studio", "corrige"), ("LOCAL COMMERCIAL", "Local commercial", "corrige")])
def test_type_bien_valides(brut, valeur, statut):
    r = normaliser_type_bien(brut)
    assert (r.valeur, r.statut) == (valeur, statut)


def test_type_bien_inconnu_et_absent():
    assert normaliser_type_bien("château").statut == "erreur"
    assert normaliser_type_bien(None).statut == "absent"
    assert normaliser_type_bien("  ").statut == "absent"


@pytest.mark.parametrize("brut", ["FCFA/mois", "par mois", "mens.", "Mensuel", "/mois"])
def test_periodicite_mensuelle(brut):
    assert normaliser_periodicite(brut).valeur == "mensuel"


def test_periodicite_jamais_devinee():
    assert normaliser_periodicite(None).statut == "absent"
    assert normaliser_periodicite("FCFA").statut == "erreur"   # 'FCFA' seul ne dit rien de la périodicité


def test_type_transaction():
    assert normaliser_type_transaction("Vente").valeur == "vente"
    assert normaliser_type_transaction("échange").statut == "erreur"


def test_inference_transaction_agence():
    assert inferer_type_transaction("Loué", 450_000).valeur == "location"
    assert inferer_type_transaction("Vendu", 60_000_000).valeur == "vente"
    r = inferer_type_transaction("Disponible", 350_000)
    assert (r.valeur, r.statut) == ("location", "corrige") and "montant" in r.motif
    assert inferer_type_transaction("Disponible", 90_000_000).valeur == "vente"
    assert inferer_type_transaction("Disponible", 0).statut == "ambigu"        # montant 0 : on ne devine pas
    assert inferer_type_transaction(None, None).statut == "ambigu"


def test_localisation_normalisation_et_coherence():
    r = normaliser_localisation("THIES", "thies", INDEX)
    assert r["region"].valeur == "Thiès" and r["ville"].valeur == "Thiès" and r["coherent"] is True


def test_localisation_incoherente_non_corrigee():
    r = normaliser_localisation("Fatick", "Dakar", INDEX)           # cas réel : région/ville contradictoires
    assert r["coherent"] is False
    assert r["region"].valeur == "Fatick" and r["ville"].valeur == "Dakar"   # aucune correction


def test_region_deduite_seulement_si_ville_unique():
    assert normaliser_localisation(None, "Gossas", INDEX)["region"].valeur == "Fatick"
    r = normaliser_localisation(None, "Mbour", INDEX)               # Mbour dans 2 régions : pas de déduction
    assert r["region"].valeur is None and r["coherent"] is None


def test_ville_absente_non_evaluable():
    r = normaliser_localisation("Kolda", None, INDEX)
    assert r["ville"].statut == "absent" and r["coherent"] is None   # non évaluable, PAS conforme par défaut


def test_alias_ville():
    assert normaliser_localisation("Dakar", "Dkr", INDEX)["ville"].valeur == "Dakar"
