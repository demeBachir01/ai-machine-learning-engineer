import datetime as dt

import pytest

from config import settings
from src.loaders import charger_toutes_les_sources
from src.loaders.inventaire import (format_date, format_montant, format_surface, inventaire_anomalies,
                                    inventaire_vers_tableau)
from src.pipeline import charger_referentiel_geo


@pytest.mark.parametrize("valeur,attendu", [
    ("2024-03-01", "ISO AAAA-MM-JJ"),
    ("25/03/2024", "JJ/MM/AAAA (1er nombre > 12)"),
    ("01/03/2024", "JJ/MM/AAAA (ambigu, convention de source)"),
    ("32/13/2024", "JJ/MM/AAAA impossible"),
    ("hier", "relatif (hier...)"),
    ("12 mars 2024", "mois en lettres"),
    (None, "vide"), ("", "vide"),
    (dt.date(2024, 1, 1), "objet_date"),
    ("n'importe quoi", "autre/illisible"),
])
def test_format_date(valeur, attendu):
    assert format_date(valeur) == attendu


@pytest.mark.parametrize("valeur,attendu", [
    (60581000, "numérique"), ("60581000", "numérique"), (0, "numérique nul ou négatif"),
    ("-5", "numérique nul ou négatif"), ("58.29 millions", "en millions (texte)"),
    ("37 965 000 FCFA", "texte avec FCFA"), ("26 620 000", "texte avec séparateurs"),
    ("à négocier", "texte non numérique"), (None, "vide"),
])
def test_format_montant(valeur, attendu):
    assert format_montant(valeur) == attendu


@pytest.mark.parametrize("valeur,attendu", [
    (45.5, "numérique"), ("45.5", "numérique"), ("45,5", "virgule décimale"),
    ("1,250", "virgule ambiguë (3 décimales : 1,250)"), ("quatre-vingt", "texte non numérique"),
    (-30.0, "numérique nul ou négatif"), (None, "vide"), ("80 m²", "texte avec unité/séparateurs"),
])
def test_format_surface(valeur, attendu):
    assert format_surface(valeur) == attendu


@pytest.fixture(scope="module")
def inventaire():
    return inventaire_anomalies(charger_toutes_les_sources(), charger_referentiel_geo())


def test_inventaire_volumes_et_doublons_bruts(inventaire):
    assert inventaire["total_recus"] == 3184
    assert inventaire["sources"]["plateforme"]["doublons_exacts_bruts"] == 15
    assert inventaire["sources"]["notaires"]["doublons_exacts_bruts"] == 0


def test_inventaire_anomalies_attendues_detectees(inventaire):
    s = inventaire["sources"]
    assert s["notaires"]["formats_rencontres"]["date_collecte"]["JJ/MM/AAAA impossible"] == 6
    assert s["notaires"]["valeurs_manquantes"]["montant"] == 14
    assert s["agence"]["formats_rencontres"]["surface"]["numérique nul ou négatif"] == 4
    assert s["plateforme"]["formats_rencontres"]["montant"]["en millions (texte)"] == 15
    assert s["particuliers"]["formats_rencontres"]["surface"]["texte non numérique"] == 4
    assert s["historique"]["valeurs_manquantes"]["ville"] == 8
    assert s["historique"]["types_bien_a_normaliser"] == 152          # MAJUSCULES
    assert s["agence"]["colonnes_absentes_de_la_source"].count("type_transaction") == 1


def test_inventaire_ne_depasse_pas_le_perimetre_connu(inventaire):
    for s in inventaire["sources"].values():
        assert s["types_bien_inconnus"] == {} and s["villes_inconnues"] == {} and s["regions_inconnues"] == {}


def test_tableau_a_plat(inventaire):
    df = inventaire_vers_tableau(inventaire)
    assert list(df.columns) == ["source", "indicateur", "detail", "valeur"]
    assert df.loc[(df.source == "plateforme") & (df.indicateur == "doublons_exacts_bruts"), "valeur"].iloc[0] == 15
