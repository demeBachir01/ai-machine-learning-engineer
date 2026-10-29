"""Cas conformes, invalides et limites de la normalisation + validation (cahier §12), au niveau d'un enregistrement."""
import datetime as dt

import pytest

from src.processing import construire_bien
from src.validation import AVERTISSEMENT, CONFORME, QUARANTAINE, Validateur
from tests.conftest_helpers import INDEX, PLATEFORME, REF, brut

V = Validateur(reference=REF)


def statut(**kw):
    bien = construire_bien(brut(**kw), PLATEFORME, INDEX)
    d = V.valider(bien)
    return d.statut_final, d, bien


def test_cas_conforme():
    assert statut()[0] == CONFORME


@pytest.mark.parametrize("champs,motif", [
    ({"surface": "quatre-vingt"}, "surface_positive"),
    ({"date_collecte": "32/13/2024"}, "date_collecte_valide"),
    ({"date_collecte": "2027-01-01"}, "date_collecte_non_future"),
    ({"montant": "à négocier"}, "prix_vente_positif"),
    ({"montant": "0"}, "prix_vente_positif"),
    ({"surface": "-30"}, "surface_positive"),
    ({"id_local": None}, "id_local_present"),
    ({"type_bien": "Château"}, "type_bien_valide"),
    ({"type_transaction": "echange"}, "type_transaction_valide"),
])
def test_cas_invalides_en_quarantaine_avec_motif(champs, motif):
    s, d, _ = statut(**champs)
    assert s == QUARANTAINE and any(motif in m for m in d.motifs_quarantaine)


def test_date_limite_aujourd_hui_acceptee_lendemain_refusee():
    assert statut(date_collecte=REF.isoformat())[0] == CONFORME
    assert statut(date_collecte=(REF + dt.timedelta(days=1)).isoformat())[0] == QUARANTAINE


def test_prix_en_millions_corrige_et_conforme():
    s, _, bien = statut(montant="58.29 millions")
    assert s == CONFORME and bien.prix == 58_290_000 and bien.est_corrige


def test_accent_et_casse_de_la_ville_corriges():
    _, _, bien = statut(ville="THIES", region="thies")
    assert bien.ville == "Thiès" and bien.region == "Thiès" and bien.geo_coherent is True


def test_surface_1_250_villa_plausible_terrain_aussi_mais_jamais_1_25():
    _, _, villa = statut(type_bien="Villa", surface="1,250")
    assert villa.surface == 1250.0 and not villa.erreurs_conversion          # 1,25 m² invraisemblable -> lecture milliers


def test_loyer_annuel_compare_en_equivalent_mensuel():
    s, d, bien = statut(type_transaction="location", montant="1 200 000", periodicite="par an")
    assert bien.periodicite == "annuel" and bien.loyer == 1_200_000 and s == CONFORME     # 100 000 / mois : plausible
    s, d, _ = statut(type_transaction="location", montant="120 000", periodicite="par an")  # 10 000 / mois : atypique
    assert s == AVERTISSEMENT and "loyer_atypique" in " ".join(d.motifs_avertissement)


def test_loyer_sans_periodicite_conserve_avec_avertissement_sans_deviner():
    s, d, bien = statut(type_transaction="location", montant="250000", periodicite=None)
    assert s == AVERTISSEMENT and bien.periodicite is None


def test_region_ville_incoherentes_conservees_avec_avertissement():
    s, d, bien = statut(region="Ziguinchor", ville="Dakar")
    assert s == AVERTISSEMENT and bien.ville == "Dakar" and bien.region == "Ziguinchor"


def test_atypies_sont_des_avertissements_jamais_une_suppression():
    s, d, _ = statut(surface="3000")
    assert s == AVERTISSEMENT and "surface_atypique" in " ".join(d.motifs_avertissement)
