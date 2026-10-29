"""Les 5 chargeurs (phase 3). Chacun définit seulement son contexte, son mapping et `lire()`.

Règles communes : tout est lu en TEXTE (ou valeur JSON d'origine), sans conversion ; une cellule vide devient
None ; les fichiers de data/raw ne sont jamais modifiés.
"""
import json
from typing import Dict

import pandas as pd

from config import settings
from src.models import ContexteSource
from .base import ChargeurSource


def _lire_csv(nom: str, sep: str, encodage: str) -> pd.DataFrame:
    # keep_default_na=False : 'None', 'NA' restent du texte visible (erreur de conversion tracée),
    # seules les cellules réellement vides deviennent manquantes.
    return pd.read_csv(settings.RAW_DIR / nom, sep=sep, encoding=encodage, dtype=str,
                       keep_default_na=False, na_values=[""])


class ChargeurPlateforme(ChargeurSource):
    """CSV ';'. La périodicité n'a pas de colonne : elle est portée par `devise` ('FCFA/mois')."""
    contexte = ContexteSource("plateforme", "plateforme_immo_sn.csv", settings.CONVENTION_DATE["plateforme"])
    mapping: Dict[str, str] = {
        "ref_plateforme": "id_local", "date_mise_en_ligne": "date_collecte", "type_transaction": "type_transaction",
        "categorie": "type_bien", "region": "region", "commune": "ville", "quartier": "quartier",
        "prix": "montant", "devise": "periodicite", "surface": "surface", "pieces": "pieces",
        "sdb": "salles_bain", "statut": "statut",
    }
    # 'description' et 'date_expiration' : volontairement non mappées (décision 4 : expiration non contrôlée)

    def lire(self) -> pd.DataFrame:
        return _lire_csv(self.contexte.fichier, ";", "utf-8")


class ChargeurAgence(ChargeurSource):
    """Excel : la feuille 'Annonces' contient les données ; 'Params' n'est que de la métadonnée (décision 19)."""
    contexte = ContexteSource("agence", "agence_teranga.xlsx", settings.CONVENTION_DATE["agence"],
                              inferer_transaction=True)
    mapping = {
        "Code": "id_local", "Date": "date_collecte", "Region": "region", "Ville": "ville", "Type": "type_bien",
        "Prix_FCFA": "montant", "Surface_m2": "surface", "Chambres": "chambres", "SDB": "salles_bain",
        "Statut": "statut",
    }
    FEUILLE_DONNEES = "Annonces"
    FEUILLE_PARAMS = "Params"

    def lire(self) -> pd.DataFrame:
        chemin = settings.RAW_DIR / self.contexte.fichier
        feuilles = pd.read_excel(chemin, sheet_name=None, dtype=object)
        params = feuilles.get(self.FEUILLE_PARAMS)
        self.metadonnees = dict(zip(params["Parametre"], params["Valeur"])) if params is not None else {}
        donnees = [df for nom, df in feuilles.items() if nom != self.FEUILLE_PARAMS]
        if not donnees:
            raise ValueError(f"{self.contexte.fichier} : aucune feuille de données")
        # Concaténation de toutes les feuilles de données (une seule aujourd'hui) ; l'index repart à 0
        # feuille par feuille, donc la ligne d'origine n'est exacte que pour une feuille unique.
        return pd.concat(donnees, ignore_index=True) if len(donnees) > 1 else donnees[0]


class ChargeurParticuliers(ChargeurSource):
    """JSON imbriqué {annonce: {id, date, localisation:{...}, details:{...}, statut}} aplati par json_normalize."""
    contexte = ContexteSource("particuliers", "particuliers.json", settings.CONVENTION_DATE["particuliers"])
    decalage_ligne = 1   # pas d'en-tête : ligne_origine = rang de l'objet dans la liste (1 = premier)
    mapping = {
        "annonce.id": "id_local", "annonce.date": "date_collecte",
        "annonce.localisation.region": "region", "annonce.localisation.ville": "ville",
        "annonce.details.type": "type_bien", "annonce.details.transaction": "type_transaction",
        "annonce.details.prix": "montant", "annonce.details.surface": "surface",
        "annonce.details.chambres": "chambres", "annonce.details.sdb": "salles_bain",
        "annonce.statut": "statut",
    }

    def lire(self) -> pd.DataFrame:
        with open(settings.RAW_DIR / self.contexte.fichier, encoding="utf-8") as f:
            return pd.json_normalize(json.load(f)).astype(object)


class ChargeurNotaires(ChargeurSource):
    """CSV ','. Actes de vente : le type de transaction est fixé au niveau de la source (décision 9)."""
    contexte = ContexteSource("notaires", "notaires.csv", settings.CONVENTION_DATE["notaires"],
                              transaction_par_defaut="vente")
    mapping = {
        "id_acte": "id_local", "date_acte": "date_collecte", "region": "region", "ville": "ville",
        "type_bien": "type_bien", "montant_fcfa": "montant", "superficie": "surface",
        "nb_chambres": "chambres", "statut": "statut",
    }

    def lire(self) -> pd.DataFrame:
        return _lire_csv(self.contexte.fichier, ",", "utf-8")


class ChargeurHistorique(ChargeurSource):
    """CSV ';' en latin-1 ; colonne DateVente -> ventes (décision 9)."""
    contexte = ContexteSource("historique", "import_historique.csv", settings.CONVENTION_DATE["historique"],
                              transaction_par_defaut="vente")
    mapping = {
        "ID": "id_local", "DateVente": "date_collecte", "Region": "region", "Ville": "ville",
        "TypeBien": "type_bien", "Prix": "montant", "Surface": "surface", "Chambres": "chambres",
        "SallesBain": "salles_bain",
    }

    def lire(self) -> pd.DataFrame:
        return _lire_csv(self.contexte.fichier, ";", "latin-1")


# Ordre = priorité de fusion (notaires > agence > plateforme > particuliers > historique), voir settings.PRIORITE_SOURCES
TOUS_LES_CHARGEURS = (ChargeurNotaires, ChargeurAgence, ChargeurPlateforme, ChargeurParticuliers, ChargeurHistorique)


def charger_toutes_les_sources() -> Dict[str, tuple]:
    """{source: (chargeur, enregistrements bruts)} — enregistrements au schéma cible, non convertis."""
    resultat = {}
    for classe in TOUS_LES_CHARGEURS:
        chargeur = classe()
        resultat[chargeur.contexte.source] = (chargeur, chargeur.charger())
    return resultat


def dataframe_brut_unifie(sources: Dict[str, tuple]) -> pd.DataFrame:
    """Livrable phase 3 : un seul DataFrame (schéma cible + provenance), valeurs encore brutes."""
    lignes = []
    for nom, (chargeur, enregistrements) in sources.items():
        for e in enregistrements:
            lignes.append({"source": nom, "fichier": chargeur.contexte.fichier, **e})
    colonnes = ["source", "fichier", "ligne_origine", *settings.COLONNES_BRUTES_CIBLE]
    return pd.DataFrame(lignes, columns=colonnes)
