"""Inventaire initial des anomalies (phase 3) : décrit ce qui est reçu, SANS rien corriger ni supprimer."""
import datetime as dt
import re
from collections import Counter
from typing import Dict

import pandas as pd

from config import settings
from src.utils import cle_texte, est_vide

_ISO = re.compile(r"^\d{4}-\d{1,2}-\d{1,2}$")
_BARRES = re.compile(r"^(\d{1,2})/(\d{1,2})/\d{4}$")
_LETTRES = re.compile(r"^\d{1,2}(?:er)? [a-zéûô]+ \d{4}$", re.IGNORECASE)
_RELATIFS = {"hier", "aujourd'hui", "aujourdhui", "avant-hier", "avant hier"}
_NOMBRE = re.compile(r"^-?\d+(\.\d+)?$")


def format_date(valeur) -> str:
    if est_vide(valeur):
        return "vide"
    if isinstance(valeur, (dt.date, dt.datetime)):
        return "objet_date"
    t = str(valeur).strip()
    if _ISO.match(t):
        return "ISO AAAA-MM-JJ"
    m = _BARRES.match(t)
    if m:
        a, b = int(m[1]), int(m[2])
        if a > 12 and b > 12:
            return "JJ/MM/AAAA impossible"
        return "JJ/MM/AAAA (1er nombre > 12)" if a > 12 else "JJ/MM/AAAA (ambigu, convention de source)"
    if t.lower() in _RELATIFS:
        return "relatif (hier...)"
    if _LETTRES.match(t):
        return "mois en lettres"
    return "autre/illisible"


def format_montant(valeur) -> str:
    if est_vide(valeur):
        return "vide"
    if isinstance(valeur, bool):
        return "booléen"
    if isinstance(valeur, (int, float)):
        return "numérique nul ou négatif" if valeur <= 0 else "numérique"
    t = str(valeur).strip()
    bas = t.lower()
    if "million" in bas:
        return "en millions (texte)"
    if _NOMBRE.match(t):
        return "numérique nul ou négatif" if float(t) <= 0 else "numérique"
    if re.search(r"\d", t):
        if re.search(r"fcfa|cfa|xof", bas):
            return "texte avec FCFA"
        return "texte avec séparateurs"
    return "texte non numérique"


def format_surface(valeur) -> str:
    if est_vide(valeur):
        return "vide"
    if isinstance(valeur, bool):
        return "booléen"
    if isinstance(valeur, (int, float)):
        return "numérique nul ou négatif" if valeur <= 0 else "numérique"
    t = str(valeur).strip()
    if _NOMBRE.match(t):
        return "numérique nul ou négatif" if float(t) <= 0 else "numérique"
    if re.match(r"^\d{1,3},\d{3}$", t):
        return "virgule ambiguë (3 décimales : 1,250)"
    if re.match(r"^\d+,\d+$", t):
        return "virgule décimale"
    if re.search(r"\d", t):
        return "texte avec unité/séparateurs"
    return "texte non numérique"


_FORMATS = {"date_collecte": format_date, "montant": format_montant, "surface": format_surface}


def _non_reconnus(valeurs, reference: set) -> Dict[str, int]:
    return dict(Counter(str(v) for v in valeurs if not est_vide(v) and cle_texte(v) not in reference).most_common(10))


def inventaire_anomalies(sources: Dict[str, tuple], index_geo: dict) -> dict:
    """Inventaire par source : volumes, manquants, formats, doublons exacts bruts, valeurs hors référentiel."""
    cles_types = set(settings.SYNONYMES_TYPE_BIEN)
    cles_villes = set(index_geo["noms_villes"]) | set(settings.ALIAS_VILLE)
    cles_regions = set(index_geo["regions"])
    resultat = {"total_recus": 0, "sources": {}}
    for nom, (chargeur, enregistrements) in sources.items():
        df = pd.DataFrame(enregistrements)
        colonnes = [c for c in settings.COLONNES_BRUTES_CIBLE if c in chargeur.mapping.values()]
        valeurs_cols = [c for c in df.columns if c != "ligne_origine"]
        doublons = int(df.duplicated(subset=valeurs_cols).sum())
        manquants = {c: int(df[c].map(est_vide).sum()) for c in colonnes}
        resultat["sources"][nom] = {
            "fichier": chargeur.contexte.fichier,
            "lignes": len(df),
            "colonnes_mappees": {src: cible for src, cible in chargeur.mapping.items()},
            "colonnes_non_mappees": chargeur.colonnes_non_mappees(chargeur.lire()),
            "metadonnees": getattr(chargeur, "metadonnees", {}),
            "colonnes_absentes_de_la_source": [c for c in settings.COLONNES_BRUTES_CIBLE if c not in colonnes],
            "valeurs_manquantes": manquants,
            "formats_rencontres": {champ: dict(Counter(f(v) for v in df[champ]))
                                   for champ, f in _FORMATS.items() if champ in colonnes},
            "doublons_exacts_bruts": doublons,
            "taux_doublons_exacts_pct": round(100 * doublons / len(df), 2) if len(df) else None,
            "types_bien_a_normaliser": int(sum(1 for v in df["type_bien"]
                                               if not est_vide(v) and str(v) not in settings.TYPES_BIEN)),
            "types_bien_inconnus": _non_reconnus(df["type_bien"], cles_types),
            "villes_inconnues": _non_reconnus(df["ville"], cles_villes),
            "regions_inconnues": _non_reconnus(df["region"], cles_regions),
        }
        resultat["total_recus"] += len(df)
    return resultat


def inventaire_vers_tableau(inventaire: dict) -> pd.DataFrame:
    """Vue à plat (source, indicateur, détail, valeur) pour reports/inventaire_anomalies.csv."""
    lignes = []
    for nom, s in inventaire["sources"].items():
        lignes.append((nom, "lignes", "", s["lignes"]))
        lignes.append((nom, "doublons_exacts_bruts", "", s["doublons_exacts_bruts"]))
        for col, n in s["valeurs_manquantes"].items():
            lignes.append((nom, "valeurs_manquantes", col, n))
        for champ, formats in s["formats_rencontres"].items():
            for fmt, n in formats.items():
                lignes.append((nom, f"format_{champ}", fmt, n))
        lignes.append((nom, "types_bien_a_normaliser", "", s["types_bien_a_normaliser"]))
    return pd.DataFrame(lignes, columns=["source", "indicateur", "detail", "valeur"])
