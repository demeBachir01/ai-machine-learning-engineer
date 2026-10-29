"""Traitement : transforme un enregistrement brut (dict) en `Bien` normalisé, en traçant chaque correction.

Responsabilité unique : convertir et normaliser. Ce module ne décide JAMAIS de la quarantaine
(c'est le rôle du module validation).
"""
import datetime as dt
from typing import Optional

from src.models import Bien, ContexteSource, Correction
from src.utils import (Resultat, est_vide, inferer_type_transaction, normaliser_localisation,
                       normaliser_periodicite, normaliser_type_bien, normaliser_type_transaction,
                       parse_date, parse_entier, parse_prix, parse_surface)


def _appliquer(bien: Bien, champ: str, res: Resultat, ancienne) -> None:
    """Range le résultat d'une conversion : valeur, correction tracée ou erreur de conversion."""
    if res.exploitable:
        setattr(bien, champ, res.valeur)
        if res.statut == "corrige":
            bien.corrections.append(Correction(champ, ancienne, res.valeur, res.motif))
    elif res.statut in ("erreur", "ambigu"):
        bien.erreurs_conversion[champ] = res.motif
    # 'absent' : la valeur reste None, c'est la validation qui jugera si c'est bloquant


def _texte_ou_none(valeur) -> Optional[str]:
    return None if est_vide(valeur) else str(valeur).strip()


def _transaction(brut: dict, contexte: ContexteSource) -> tuple:
    """Retourne (Resultat, est_inference). Une valeur déduite n'est pas une correction : la source ne
    la contenait pas. Elle est tracée à part (Bien.inferences) pour ne pas gonfler 'enregistrements corrigés'."""
    if not est_vide(brut.get("type_transaction")):
        return normaliser_type_transaction(brut["type_transaction"]), False
    if contexte.transaction_par_defaut:
        return Resultat(contexte.transaction_par_defaut, "ok", "transaction_par_defaut_de_la_source"), True
    if contexte.inferer_transaction:
        montant = parse_prix(brut.get("montant")).valeur
        res = inferer_type_transaction(brut.get("statut"), montant)
        return (Resultat(res.valeur, "ok", res.motif) if res.valeur else res), res.valeur is not None
    return Resultat(None, "absent", "type_transaction_absent"), False


def construire_bien(brut: dict, contexte: ContexteSource, index_geo: dict,
                    ligne_origine: Optional[int] = None) -> Bien:
    """Construit un Bien. `brut` utilise les clés de settings.COLONNES_BRUTES_CIBLE."""
    if ligne_origine is None:
        ligne_origine = brut.get("ligne_origine")
    bien = Bien(source=contexte.source, fichier=contexte.fichier, ligne_origine=ligne_origine,
                valeurs_brutes=dict(brut))

    bien.id_local = _texte_ou_none(brut.get("id_local"))
    bien.quartier = _texte_ou_none(brut.get("quartier"))
    bien.statut = _texte_ou_none(brut.get("statut"))

    # 1. Vente ou location AVANT toute normalisation de prix (cahier §6.3)
    res_transaction, infere = _transaction(brut, contexte)
    _appliquer(bien, "type_transaction", res_transaction, brut.get("type_transaction"))
    if infere:
        bien.inferences["type_transaction"] = res_transaction.motif
    _appliquer(bien, "type_bien", normaliser_type_bien(brut.get("type_bien")), brut.get("type_bien"))

    # 2. Montant : prix si vente, loyer + périodicité si location, rien si transaction inconnue
    montant = brut.get("montant")
    if bien.type_transaction == "vente":
        _appliquer(bien, "prix", parse_prix(montant), montant)
    elif bien.type_transaction == "location":
        _appliquer(bien, "loyer", parse_prix(montant), montant)
        _appliquer(bien, "periodicite", normaliser_periodicite(brut.get("periodicite")), brut.get("periodicite"))

    # 3. Caractéristiques
    _appliquer(bien, "surface", parse_surface(brut.get("surface")), brut.get("surface"))
    for champ in ("pieces", "chambres", "salles_bain"):
        _appliquer(bien, champ, parse_entier(brut.get(champ), champ), brut.get(champ))

    # 4. Dates : une date relative n'est résolue que par rapport à une date connue (jamais devinée)
    _appliquer(bien, "date_collecte", parse_date(brut.get("date_collecte"), contexte.convention_date),
               brut.get("date_collecte"))
    _appliquer(bien, "date_mise_a_jour",
               parse_date(brut.get("date_mise_a_jour"), contexte.convention_date, reference=bien.date_collecte),
               brut.get("date_mise_a_jour"))

    # 5. Localisation : normalisée, jamais corrigée en cas d'incohérence
    loc = normaliser_localisation(brut.get("region"), brut.get("ville"), index_geo)
    _appliquer(bien, "region", loc["region"], brut.get("region"))
    _appliquer(bien, "ville", loc["ville"], brut.get("ville"))
    bien.geo_coherent = loc["coherent"]
    return bien
