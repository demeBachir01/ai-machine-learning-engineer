import math
import pytest

from src.utils import parse_prix, parse_surface, parse_entier, prix_au_m2, loyer_mensuel_equivalent


@pytest.mark.parametrize("brut,valeur,statut", [
    (60581000, 60_581_000.0, "ok"),
    ("37 965 000 FCFA", 37_965_000.0, "corrige"),
    ("58.29 millions", 58_290_000.0, "corrige"),
    ("57,62 millions", 57_620_000.0, "corrige"),
    ("1,250,000", 1_250_000.0, "corrige"),
    ("26 620 000", 26_620_000.0, "corrige"),
    ("320860000.0", 320_860_000.0, "ok"),
    ("60581000", 60_581_000.0, "ok"),
    ("210000 FCFA", 210_000.0, "corrige"),
])
def test_prix_valides(brut, valeur, statut):
    r = parse_prix(brut)
    assert r.valeur == pytest.approx(valeur) and r.statut == statut


@pytest.mark.parametrize("brut,statut", [("à négocier", "erreur"), ("None FCFA", "erreur"),
                                         (None, "absent"), ("", "absent"), (float("nan"), "absent"),
                                         (float("inf"), "erreur"), ("1.250", "ambigu")])
def test_prix_invalides(brut, statut):
    r = parse_prix(brut)
    assert r.statut == statut and r.valeur is None


def test_prix_nul_ou_negatif_est_converti_mais_pas_valide():
    # la conversion réussit ; c'est la règle de validation (phase 4) qui mettra en quarantaine
    assert parse_prix(0).valeur == 0.0 and parse_prix("-5000").valeur == -5000.0


@pytest.mark.parametrize("brut,valeur", [("173.3", 173.3), ("173,3", 173.3), (50.0, 50.0), ("45 m²", 45.0)])
def test_surface_valides(brut, valeur):
    assert parse_surface(brut).valeur == pytest.approx(valeur)


def test_surface_virgule_ambigue_resolue_par_plausibilite():
    r = parse_surface("1,250")                    # 1,25 m² invraisemblable -> 1 250 m²
    assert r.valeur == 1250.0 and r.statut == "corrige" and r.motif.endswith("milliers")
    r = parse_surface("125,500")                  # 125 500 m² invraisemblable -> 125,5 m²
    assert r.valeur == 125.5 and r.motif.endswith("decimale")


def test_surface_virgule_indecidable():
    r = parse_surface("0,001")                    # 0,001 et 1 sont tous deux invraisemblables
    assert r.statut == "ambigu" and r.valeur is None


@pytest.mark.parametrize("brut,statut", [("quatre-vingt", "erreur"), (None, "absent"), ("abc", "erreur")])
def test_surface_invalides(brut, statut):
    assert parse_surface(brut).statut == statut


def test_surface_negative_conservee_pour_la_validation():
    assert parse_surface("-30").valeur == -30.0


def test_entiers():
    assert parse_entier(3).valeur == 3
    assert parse_entier("4").statut == "ok" and parse_entier("4").valeur == 4 and parse_entier(2.0).valeur == 2
    assert parse_entier(2.5).statut == "erreur" and parse_entier("trois").statut == "erreur"
    assert parse_entier(None).statut == "absent"


def test_prix_au_m2():
    assert prix_au_m2(60_000_000, 100) == 600_000
    assert prix_au_m2(None, 100) is None and prix_au_m2(1000, 0) is None and prix_au_m2(-5, 10) is None


def test_loyer_mensuel_equivalent():
    assert loyer_mensuel_equivalent(300_000, "trimestriel") == 100_000
    assert loyer_mensuel_equivalent(1_200_000, "annuel") == 100_000
    assert loyer_mensuel_equivalent(300_000, None) is None        # périodicité inconnue : on ne devine pas


def test_chaine_numerique_propre_nest_pas_une_correction():
    assert parse_prix("60581000").statut == "ok"
    assert parse_surface("173.3").statut == "ok"
    assert parse_surface("173,3").statut == "corrige"      # virgule décimale = vraie correction
