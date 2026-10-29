"""Fabriques partagées par les tests de la phase 2."""
import datetime as dt

import pandas as pd

from src.models import ContexteSource
from src.utils import construire_index_geo

REF = dt.date(2026, 10, 29)
GEO = pd.DataFrame({"region": ["Dakar", "Dakar", "Thiès", "Thiès", "Fatick", "Ziguinchor"],
                    "ville": ["Dakar", "Pikine", "Thiès", "Mbour", "Gossas", "Ziguinchor"]})
INDEX = construire_index_geo(GEO)
PLATEFORME = ContexteSource("plateforme", "plateforme_immo_sn.csv", "JJ/MM")
AGENCE = ContexteSource("agence", "agence_teranga.xlsx", "JJ/MM", inferer_transaction=True)
NOTAIRES = ContexteSource("notaires", "notaires.csv", "JJ/MM", transaction_par_defaut="vente")


def brut(**kw) -> dict:
    """Enregistrement brut d'une vente valide ; chaque test modifie un seul champ."""
    base = {"id_local": "PLT-1", "type_transaction": "vente", "type_bien": "Appartement", "region": "Dakar",
            "ville": "Dakar", "quartier": "Centre", "montant": "60581000", "periodicite": None,
            "surface": "90.5", "pieces": "3", "chambres": "2", "salles_bain": "1",
            "date_collecte": "2022-09-15", "date_mise_a_jour": None, "statut": "En vente"}
    base.update(kw)
    return base
