"""Fonctions simples de filtrage, de comptage et de vérification sur des biens (dictionnaires).

Un bien est un dict avec les clés du schéma cible : type_transaction, type_bien, ville, prix, loyer,
periodicite, surface, chambres, salles_bain... Les valeurs manquantes sont None.
"""
from collections import Counter
from typing import Callable, Iterable

from config import settings
from .numbers import loyer_mensuel_equivalent, prix_au_m2


def filtrer(biens: Iterable[dict], **criteres) -> list:
    """Filtre par égalité ou par prédicat : filtrer(biens, type_bien="Villa", surface=lambda s: s and s > 100)."""
    def correspond(bien: dict) -> bool:
        for champ, attendu in criteres.items():
            valeur = bien.get(champ)
            if callable(attendu):
                if not attendu(valeur):
                    return False
            elif valeur != attendu:
                return False
        return True
    return [b for b in biens if correspond(b)]


def compter_par(biens: Iterable[dict], champ: str) -> dict:
    """Effectifs par valeur d'un champ ; None est compté sous la clé 'manquant'."""
    return dict(Counter(b.get(champ) if b.get(champ) is not None else "manquant" for b in biens))


def valeurs_manquantes(biens: list, champs: Iterable[str]) -> dict:
    """Nombre de valeurs manquantes par champ (clé absente ou valeur None)."""
    return {champ: sum(1 for b in biens if b.get(champ) is None) for champ in champs}


def detecter_doublons_exacts(biens: list, champs: Iterable[str]) -> list:
    """Indices des biens dont le tuple de valeurs `champs` a déjà été vu (la 1re occurrence n'est pas comptée).

    Un ensemble de tuples sert de mémoire : tester l'appartenance coûte O(1).
    """
    vus, doublons = set(), []
    champs = tuple(champs)
    for i, bien in enumerate(biens):
        cle = tuple(bien.get(c) for c in champs)
        if cle in vus:
            doublons.append(i)
        else:
            vus.add(cle)
    return doublons


def verifier_atypies(bien: dict) -> list:
    """Liste des AVERTISSEMENTS (jamais de suppression) applicables à un bien.

    Chaque motif est un code stable, utilisable dans le rapport de qualité.
    Les champs manquants rendent la règle non évaluable : elle ne produit ni avertissement ni conformité.
    """
    motifs = []
    type_bien = bien.get("type_bien")
    surface = bien.get("surface")
    transaction = bien.get("type_transaction")

    if surface is not None:
        if surface < settings.SURFACE_ATYPIQUE_MIN or surface > settings.SURFACE_ATYPIQUE_MAX:
            motifs.append("surface_atypique")
        if type_bien in settings.FOURCHETTES:
            _, _, s_min, s_max = settings.FOURCHETTES[type_bien]
            if not s_min <= surface <= s_max:
                motifs.append("surface_hors_fourchette_type")

    if transaction == "vente":
        prix = bien.get("prix")
        if prix is not None:
            if prix < settings.PRIX_ATYPIQUE_MIN or prix > settings.PRIX_ATYPIQUE_MAX:
                motifs.append("prix_atypique")
            if type_bien in settings.FOURCHETTES:
                p_min, p_max, s_min, s_max = settings.FOURCHETTES[type_bien]
                if not p_min <= prix <= p_max:
                    motifs.append("prix_hors_fourchette_type")
                m2 = prix_au_m2(prix, surface)
                # Option A (large) : borne basse = prix_min / surface_max ; borne haute = prix_max / surface_min
                if m2 is not None and not p_min / s_max <= m2 <= p_max / s_min:
                    motifs.append("prix_m2_hors_fourchette_type")
    elif transaction == "location":
        mensuel = loyer_mensuel_equivalent(bien.get("loyer"), bien.get("periodicite"))
        if mensuel is not None and not settings.LOYER_MIN_MENSUEL <= mensuel <= settings.LOYER_MAX_MENSUEL:
            motifs.append("loyer_atypique")

    chambres, sdb = bien.get("chambres"), bien.get("salles_bain")
    if chambres is not None and type_bien in ("Appartement", "Studio") \
            and chambres > settings.MAX_CHAMBRES_APPART_STUDIO:
        motifs.append("chambres_atypiques")
    if chambres is not None and sdb is not None and sdb > chambres + settings.SDB_MARGE_SUR_CHAMBRES:
        motifs.append("sdb_superieures_chambres_plus_marge")
    if type_bien == "Terrain" and ((chambres or 0) > 0 or (sdb or 0) > 0):
        motifs.append("terrain_avec_pieces")
    if type_bien == "Chambre" and chambres is not None and chambres > 1:
        motifs.append("chambre_avec_plusieurs_chambres")
    return motifs
