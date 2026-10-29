from src.utils import filtrer, compter_par, valeurs_manquantes, detecter_doublons_exacts, verifier_atypies

BIENS = [
    {"id": "A1", "type_transaction": "vente", "type_bien": "Villa", "ville": "Dakar", "prix": 200_000_000, "surface": 250, "chambres": 4, "salles_bain": 3},
    {"id": "A2", "type_transaction": "vente", "type_bien": "Studio", "ville": "Thiès", "prix": 18_000_000, "surface": 30, "chambres": 1, "salles_bain": 1},
    {"id": "A3", "type_transaction": "location", "type_bien": "Appartement", "ville": "Dakar", "loyer": 300_000, "periodicite": "mensuel", "surface": 80, "chambres": 3, "salles_bain": 2},
    {"id": "A1", "type_transaction": "vente", "type_bien": "Villa", "ville": "Dakar", "prix": 200_000_000, "surface": 250, "chambres": 4, "salles_bain": 3},
    {"id": "A5", "type_transaction": "vente", "type_bien": "Maison", "ville": None, "prix": None, "surface": 100},
]


def test_filtrer_egalite_et_predicat():
    assert len(filtrer(BIENS, type_bien="Villa")) == 2
    assert [b["id"] for b in filtrer(BIENS, ville="Dakar", surface=lambda s: s is not None and s > 100)] == ["A1", "A1"]
    assert filtrer(BIENS, type_bien="Hôtel") == []


def test_compter_et_manquants():
    assert compter_par(BIENS, "ville") == {"Dakar": 3, "Thiès": 1, "manquant": 1}
    assert valeurs_manquantes(BIENS, ["prix", "ville"])["ville"] == 1
    assert valeurs_manquantes([], ["prix"]) == {"prix": 0}


def test_doublons_exacts():
    assert detecter_doublons_exacts(BIENS, ["id", "type_bien", "ville", "prix", "surface"]) == [3]
    assert detecter_doublons_exacts([], ["id"]) == []


def test_bien_conforme_sans_avertissement():
    assert verifier_atypies(BIENS[0]) == []
    assert verifier_atypies(BIENS[2]) == []


def test_avertissements_surface_et_prix():
    b = {"type_transaction": "vente", "type_bien": "Villa", "prix": 50_000, "surface": 3}
    m = verifier_atypies(b)
    assert {"surface_atypique", "prix_atypique", "surface_hors_fourchette_type", "prix_hors_fourchette_type"} <= set(m)


def test_loyer_selon_periodicite():
    # 600 000 / trimestre = 200 000 / mois -> conforme ; 60 000 / an = 5 000 / mois -> atypique
    base = {"type_transaction": "location", "type_bien": "Appartement"}
    assert "loyer_atypique" not in verifier_atypies({**base, "loyer": 600_000, "periodicite": "trimestriel"})
    assert "loyer_atypique" in verifier_atypies({**base, "loyer": 60_000, "periodicite": "annuel"})
    assert "loyer_atypique" not in verifier_atypies({**base, "loyer": 10_000, "periodicite": None})  # non évaluable


def test_chambres_et_sdb():
    assert "chambres_atypiques" in verifier_atypies({"type_bien": "Studio", "chambres": 11})
    assert "chambres_atypiques" not in verifier_atypies({"type_bien": "Villa", "chambres": 11})
    assert "chambres_atypiques" not in verifier_atypies({"type_bien": "Studio", "chambres": 10})   # limite incluse
    assert "sdb_superieures_chambres_plus_marge" in verifier_atypies({"chambres": 1, "salles_bain": 4})
    assert "sdb_superieures_chambres_plus_marge" not in verifier_atypies({"chambres": 1, "salles_bain": 3})  # limite
    assert "terrain_avec_pieces" in verifier_atypies({"type_bien": "Terrain", "chambres": 2})


def test_champs_manquants_aucun_avertissement_ni_plantage():
    assert verifier_atypies({}) == []
