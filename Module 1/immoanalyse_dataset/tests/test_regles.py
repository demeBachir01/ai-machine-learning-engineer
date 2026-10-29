import pytest

from src.processing import construire_bien
from src.validation import Action, StatutRegle, construire_regles
from tests.conftest_helpers import INDEX, PLATEFORME, REF, brut

REGLES = {r.nom: r for r in construire_regles(REF)}


def statut(nom, **kw):
    return REGLES[nom].appliquer(construire_bien(brut(**kw), PLATEFORME, INDEX)).statut


def test_noms_de_regles_uniques_et_actions_valides():
    noms = [r.nom for r in construire_regles(REF)]
    assert len(noms) == len(set(noms)) >= 20
    assert all(isinstance(r.action, Action) for r in construire_regles(REF))


@pytest.mark.parametrize("nom,kw,attendu", [
    ("id_local_present", {}, StatutRegle.CONFORME),
    ("id_local_present", {"id_local": None}, StatutRegle.NON_CONFORME),
    ("id_local_present", {"id_local": "  "}, StatutRegle.NON_CONFORME),
    ("prix_vente_positif", {}, StatutRegle.CONFORME),
    ("prix_vente_positif", {"montant": "0"}, StatutRegle.NON_CONFORME),
    ("prix_vente_positif", {"montant": "-5000"}, StatutRegle.NON_CONFORME),
    ("prix_vente_positif", {"montant": "à négocier"}, StatutRegle.NON_CONFORME),
    ("prix_vente_positif", {"type_transaction": "location"}, StatutRegle.NON_EVALUABLE),
    ("loyer_positif", {"type_transaction": "location"}, StatutRegle.CONFORME),
    ("loyer_positif", {}, StatutRegle.NON_EVALUABLE),
    ("surface_positive", {"surface": "-30"}, StatutRegle.NON_CONFORME),
    ("surface_positive", {"surface": None}, StatutRegle.NON_CONFORME),
    ("surface_positive", {"surface": "quatre-vingt"}, StatutRegle.NON_CONFORME),
    ("date_collecte_valide", {"date_collecte": "32/13/2024"}, StatutRegle.NON_CONFORME),
    ("date_collecte_non_future", {"date_collecte": "2026-10-29"}, StatutRegle.CONFORME),     # limite : aujourd'hui
    ("date_collecte_non_future", {"date_collecte": "2026-10-30"}, StatutRegle.NON_CONFORME),
    ("date_collecte_non_future", {"date_collecte": "32/13/2024"}, StatutRegle.NON_EVALUABLE),
    ("type_bien_valide", {"type_bien": "château"}, StatutRegle.NON_CONFORME),
    ("type_bien_valide", {"type_bien": "VILLA"}, StatutRegle.CONFORME),
    ("type_transaction_valide", {"type_transaction": "échange"}, StatutRegle.NON_CONFORME),
    ("periodicite_valide", {"type_transaction": "location", "montant": "250000"}, StatutRegle.NON_CONFORME),
    ("periodicite_valide", {"type_transaction": "location", "montant": "250000", "periodicite": "/mois"}, StatutRegle.CONFORME),
    ("region_ville_coherentes", {}, StatutRegle.CONFORME),
    ("region_ville_coherentes", {"region": "Fatick", "ville": "Dakar"}, StatutRegle.NON_CONFORME),
    ("region_ville_coherentes", {"ville": None}, StatutRegle.NON_EVALUABLE),
    ("chambres_entier_positif_ou_nul", {"chambres": "-1"}, StatutRegle.NON_CONFORME),
    ("chambres_entier_positif_ou_nul", {"chambres": "2.5"}, StatutRegle.NON_CONFORME),
    ("chambres_entier_positif_ou_nul", {"chambres": None}, StatutRegle.NON_EVALUABLE),
    ("chambres_entier_positif_ou_nul", {"chambres": "0"}, StatutRegle.CONFORME),             # limite : 0 est valide
])
def test_regles_cas_conformes_invalides_limites(nom, kw, attendu):
    assert statut(nom, **kw) == attendu


def test_regles_atypies():
    assert statut("surface_atypique", surface="3") == StatutRegle.NON_CONFORME
    assert statut("surface_atypique", surface="5") == StatutRegle.CONFORME            # limite incluse
    assert statut("prix_atypique", montant="50000") == StatutRegle.NON_CONFORME
    assert statut("prix_hors_fourchette_type", type_bien="Villa", montant="20000000") == StatutRegle.NON_CONFORME
    assert statut("chambres_atypiques", chambres="11") == StatutRegle.NON_CONFORME
    assert statut("chambres_atypiques", chambres="10") == StatutRegle.CONFORME
    assert statut("chambres_atypiques", type_bien="Villa", chambres="11") == StatutRegle.NON_EVALUABLE
    assert statut("sdb_superieures_chambres_plus_marge", chambres="1", salles_bain="4") == StatutRegle.NON_CONFORME
    assert statut("terrain_avec_pieces", type_bien="Terrain", chambres="2") == StatutRegle.NON_CONFORME
    assert statut("prix_m2_hors_fourchette_type", surface=None) == StatutRegle.NON_EVALUABLE


def test_loyer_atypique_depend_de_la_periodicite():
    loc = {"type_transaction": "location", "montant": "60000"}
    assert statut("loyer_atypique", **loc, periodicite="annuel") == StatutRegle.NON_CONFORME   # 5 000 / mois
    assert statut("loyer_atypique", **loc, periodicite="mensuel") == StatutRegle.CONFORME
    assert statut("loyer_atypique", **loc) == StatutRegle.NON_EVALUABLE                         # périodicité inconnue


def test_detail_de_conversion_dans_le_resultat():
    b = construire_bien(brut(montant="à négocier"), PLATEFORME, INDEX)
    r = REGLES["prix_vente_positif"].appliquer(b)
    assert r.statut == StatutRegle.NON_CONFORME and "prix_non_numerique" in r.detail
