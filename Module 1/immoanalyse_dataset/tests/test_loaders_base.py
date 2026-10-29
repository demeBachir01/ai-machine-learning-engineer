import pandas as pd
import pytest

from src.loaders import ChargeurSource
from src.models import ContexteSource


class ChargeurFactice(ChargeurSource):
    contexte = ContexteSource("factice", "factice.csv")
    mapping = {"Code": "id_local", "Prix": "montant", "Date": "date_collecte"}

    def __init__(self, df):
        self._df = df

    def lire(self):
        return self._df


def test_renommage_provenance_et_nan_vers_none():
    c = ChargeurFactice(pd.DataFrame({"Code": ["A1", "A2"], "Prix": ["100", None], "Date": ["2020-01-01", "2020-01-02"], "Extra": [1, 2]}))
    lignes = c.charger()
    assert lignes[0]["id_local"] == "A1" and lignes[0]["ligne_origine"] == 2
    assert lignes[1]["montant"] is None and lignes[1]["ligne_origine"] == 3
    assert lignes[0]["type_bien"] is None                      # toutes les clés cibles existent
    assert c.colonnes_non_mappees(c.lire()) == ["Extra"]


def test_colonne_attendue_absente_est_une_erreur_explicite():
    with pytest.raises(ValueError, match="absentes"):
        ChargeurFactice(pd.DataFrame({"Code": ["A1"]})).charger()


def test_mapping_vers_colonne_cible_inconnue():
    class Mauvais(ChargeurFactice):
        mapping = {"Code": "n_importe_quoi"}
    with pytest.raises(ValueError, match="inconnues"):
        Mauvais(pd.DataFrame({"Code": ["A1"]})).charger()


def test_chargeur_abstrait_non_instanciable():
    with pytest.raises(TypeError):
        ChargeurSource()
