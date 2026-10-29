"""Normalisation de textes : clés de comparaison, types de bien, transaction, périodicité, localisation."""
import unicodedata
from typing import Optional

import pandas as pd

from config import settings
from .resultat import Resultat


def est_vide(valeur) -> bool:
    """True pour None, NaN, chaîne vide ou espaces."""
    if valeur is None:
        return True
    try:
        if pd.isna(valeur):
            return True
    except (TypeError, ValueError):
        pass
    return isinstance(valeur, str) and not valeur.strip()


def cle_texte(valeur) -> str:
    """Minuscules, sans accents, espaces réduits. Sert de clé de comparaison."""
    s = unicodedata.normalize("NFD", str(valeur).strip().lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(s.split())


def _normaliser_par_dictionnaire(valeur, dictionnaire: dict, nom_champ: str) -> Resultat:
    if est_vide(valeur):
        return Resultat(None, "absent", f"{nom_champ}_absent")
    cle = cle_texte(valeur)
    if cle in dictionnaire:
        canonique = dictionnaire[cle]
        statut = "ok" if str(valeur) == canonique else "corrige"
        return Resultat(canonique, statut, None if statut == "ok" else f"{nom_champ}_normalise")
    return Resultat(None, "erreur", f"{nom_champ}_inconnu:{valeur}")


def normaliser_type_bien(valeur) -> Resultat:
    """'appart', 'APPARTEMENT' -> 'Appartement'. Inconnu -> erreur (quarantaine, cahier §6.1)."""
    return _normaliser_par_dictionnaire(valeur, settings.SYNONYMES_TYPE_BIEN, "type_bien")


def normaliser_type_transaction(valeur) -> Resultat:
    return _normaliser_par_dictionnaire(valeur, settings.SYNONYMES_TRANSACTION, "type_transaction")


def normaliser_periodicite(valeur) -> Resultat:
    """'FCFA/mois', 'par mois', 'mens.' -> 'mensuel'. Jamais devinée : absent -> absent."""
    return _normaliser_par_dictionnaire(valeur, settings.SYNONYMES_PERIODICITE, "periodicite")


def inferer_type_transaction(statut, montant) -> Resultat:
    """Pour l'agence (type_transaction absent de la source).

    Règle documentée : statut 'Loué' -> location ; 'Vendu'/'En vente' -> vente ;
    'Disponible' (ambigu) -> on compare le montant au seuil SEUIL_LOYER_VS_PRIX.
    Toute inférence est marquée 'corrige' avec son motif : elle n'est jamais silencieuse.
    """
    s = cle_texte(statut) if not est_vide(statut) else ""
    if s == "loue":
        return Resultat("location", "corrige", "inferee_depuis_statut_loue")
    if s in ("vendu", "en vente"):
        return Resultat("vente", "corrige", f"inferee_depuis_statut_{s.replace(' ', '_')}")
    if montant is not None and not est_vide(montant) and float(montant) > 0:
        valeur = "location" if float(montant) < settings.SEUIL_LOYER_VS_PRIX else "vente"
        return Resultat(valeur, "corrige", "inferee_depuis_ordre_de_grandeur_du_montant")
    return Resultat(None, "ambigu", "transaction_non_deductible")


def construire_index_geo(df_geo: pd.DataFrame) -> dict:
    """Index du référentiel géographique.

    - 'noms_villes' : {cle_ville: nom canonique accentué}
    - 'villes_uniques' : {cle_ville: région} pour les villes présentes dans UNE seule région
      (seules celles-ci permettent de déduire la région)
    - 'regions' : {cle_region: nom canonique}
    - 'couples' : ensemble des (cle_region, cle_ville) valides
    """
    noms, regions_par_ville, regions, couples = {}, {}, {}, set()
    for region, ville in zip(df_geo["region"], df_geo["ville"]):
        cr, cv = cle_texte(region), cle_texte(ville)
        regions[cr] = region
        noms[cv] = ville
        couples.add((cr, cv))
        regions_par_ville.setdefault(cv, set()).add(region)
    uniques = {cv: next(iter(r)) for cv, r in regions_par_ville.items() if len(r) == 1}
    return {"noms_villes": noms, "villes_uniques": uniques, "regions": regions, "couples": couples}


def normaliser_localisation(region, ville, index: dict) -> dict:
    """Normalise région et ville et vérifie leur cohérence. Ne corrige JAMAIS une incohérence.

    Retourne {'region': Resultat, 'ville': Resultat, 'coherent': bool|None}.
    coherent=None : non évaluable (région ou ville inconnue/absente).
    Si la région est absente mais la ville est unique dans le référentiel, la région est déduite (preuve).
    """
    res_ville = _resoudre_ville(ville, index)
    if est_vide(region):
        if res_ville.exploitable:
            deduite = index["villes_uniques"].get(cle_texte(res_ville.valeur))
            if deduite is None:
                return {"region": Resultat(None, "absent", "region_absente_ville_ambigue"),
                        "ville": res_ville, "coherent": None}
            res_region = Resultat(deduite, "corrige", "region_deduite_de_la_ville")
        else:
            res_region = Resultat(None, "absent", "region_absente")
    else:
        cle = cle_texte(region)
        if cle in index["regions"]:
            canonique = index["regions"][cle]
            res_region = Resultat(canonique, "ok" if str(region) == canonique else "corrige",
                                  None if str(region) == canonique else "region_normalisee")
        else:
            res_region = Resultat(None, "erreur", f"region_inconnue:{region}")

    coherent = None
    if res_region.exploitable and res_ville.exploitable:
        coherent = (cle_texte(res_region.valeur), cle_texte(res_ville.valeur)) in index["couples"]
    return {"region": res_region, "ville": res_ville, "coherent": coherent}


def _resoudre_ville(ville, index: dict) -> Resultat:
    if est_vide(ville):
        return Resultat(None, "absent", "ville_absente")
    cle = cle_texte(ville)
    cle = cle_texte(settings.ALIAS_VILLE.get(cle, cle))
    nom = index["noms_villes"].get(cle)
    if nom is None:
        return Resultat(None, "erreur", f"ville_inconnue:{ville}")
    if str(ville) == nom:
        return Resultat(nom, "ok")
    return Resultat(nom, "corrige", "ville_normalisee")
