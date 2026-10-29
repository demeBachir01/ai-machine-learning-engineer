"""Phase 3 : les 5 chargeurs sur les vrais fichiers de data/raw (lecture seule)."""
import pytest

from config import settings
from src.loaders import (ChargeurAgence, ChargeurHistorique, ChargeurNotaires, ChargeurParticuliers,
                         ChargeurPlateforme, charger_toutes_les_sources, dataframe_brut_unifie)

VOLUMES = {ChargeurNotaires: 410, ChargeurAgence: 640, ChargeurPlateforme: 875,
           ChargeurParticuliers: 731, ChargeurHistorique: 528}


@pytest.mark.parametrize("classe,attendu", VOLUMES.items())
def test_volume_et_schema_cible_complet(classe, attendu):
    lignes = classe().charger()
    assert len(lignes) == attendu
    for cle in (*settings.COLONNES_BRUTES_CIBLE, "ligne_origine"):
        assert cle in lignes[0]


def test_total_et_dataframe_unifie_avec_provenance():
    sources = charger_toutes_les_sources()
    df = dataframe_brut_unifie(sources)
    assert len(df) == sum(VOLUMES.values()) == 3184
    assert set(df["source"]) == {"notaires", "agence", "plateforme", "particuliers", "historique"}
    assert df[["source", "fichier", "ligne_origine"]].notna().all().all()


def test_historique_latin1_accents_corrects():
    villes = {l["ville"] for l in ChargeurHistorique().charger() if l["ville"]}
    assert "Thiès" in villes and not any("�" in v or "Ã" in v for v in villes)


def test_excel_params_ignore_mais_conserve_en_metadonnees():
    c = ChargeurAgence()
    lignes = c.charger()
    assert c.metadonnees["Version"] == "2.1"
    assert all(l["id_local"].startswith("AGT-") for l in lignes)        # aucune ligne de la feuille Params


def test_json_aplati_et_ligne_origine_depuis_1():
    lignes = ChargeurParticuliers().charger()
    assert lignes[0]["id_local"] == "PRT-01461" and lignes[0]["ligne_origine"] == 1
    assert lignes[0]["region"] == "Fatick" and lignes[0]["ville"] == "Gossas"     # localisation aplatie
    assert lignes[0]["type_transaction"] == "vente"


def test_plateforme_periodicite_portee_par_la_devise_et_valeurs_non_converties():
    lignes = ChargeurPlateforme().charger()
    locations = [l for l in lignes if l["type_transaction"] == "location"]
    assert locations and all(l["periodicite"] == "FCFA/mois" for l in locations)
    assert any(isinstance(l["montant"], str) and "millions" in l["montant"] for l in lignes)   # brut préservé


def test_ligne_origine_csv_commence_a_2():
    assert ChargeurNotaires().charger()[0]["ligne_origine"] == 2


def test_source_sans_transaction_laisse_le_champ_vide():
    assert ChargeurAgence().charger()[0]["type_transaction"] is None
    assert ChargeurNotaires().charger()[0]["type_transaction"] is None   # décidé plus tard par le contexte
