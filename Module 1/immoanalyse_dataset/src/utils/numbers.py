"""Conversion de prix, surfaces et entiers. Chaque fonction retourne un Resultat, jamais une exception."""
import math
import re
from typing import Optional

from config import settings
from .resultat import Resultat
from .text import est_vide

_ESPACES = re.compile(r"[\s\u00a0\u202f]+")
_NOMBRE = re.compile(r"^-?\d+(?:[.,]\d+)?$")


def _nettoyer(texte: str) -> str:
    return _ESPACES.sub("", texte.strip().lower())


def parse_prix(valeur) -> Resultat:
    """Prix ou loyer -> float.

    Gère : nombres, '37 965 000 FCFA', '1,250,000', '58.29 millions', 'None FCFA', 'à négocier'.
    La positivité n'est PAS vérifiée ici (règle de validation, pas de conversion).
    """
    if est_vide(valeur):
        return Resultat(None, "absent", "prix_absent")
    if isinstance(valeur, bool):
        return Resultat(None, "erreur", "prix_booleen")
    if isinstance(valeur, (int, float)):
        if isinstance(valeur, float) and not math.isfinite(valeur):
            return Resultat(None, "erreur", "prix_non_fini")
        return Resultat(float(valeur), "ok")

    brut = str(valeur).strip()
    if re.fullmatch(r"-?\d+(?:\.\d+)?", brut) and not re.fullmatch(r"-?\d{1,3}\.\d{3}", brut):
        # déjà un nombre propre écrit en texte (ex. CSV lu en str) ; '1.250' reste ambigu (milliers ou décimale ?)
        return Resultat(float(brut), "ok")
    texte = brut.lower()
    multiplicateur = 1
    if re.search(r"\bmillions?\b", texte):
        multiplicateur = 1_000_000
        texte = re.sub(r"\bmillions?\b", "", texte)
    texte = re.sub(r"f\s?cfa|cfa|xof", "", texte)
    nombre = _nettoyer(texte)
    if not nombre or nombre == "none" or not re.match(r"^-?[\d.,]+$", nombre):
        return Resultat(None, "erreur", f"prix_non_numerique:{valeur}")

    if multiplicateur == 1_000_000:
        # '58,29 millions' : la virgule est décimale quand l'unité est explicite
        nombre = nombre.replace(",", ".")
        if not _NOMBRE.match(nombre):
            return Resultat(None, "erreur", f"prix_millions_illisible:{valeur}")
        return Resultat(float(nombre) * multiplicateur, "corrige", "prix_millions_converti")

    # Sans unité : la virgule est un séparateur de milliers (regles_metier.md)
    if "," in nombre:
        nombre = nombre.replace(",", "")
    if nombre.count(".") > 1:                 # '1.250.000'
        nombre = nombre.replace(".", "")
    elif re.match(r"^-?\d{1,3}\.\d{3}$", nombre):   # '1.250' : milliers ou décimale ?
        return Resultat(None, "ambigu", f"prix_point_ambigu:{valeur}")
    if not _NOMBRE.match(nombre):
        return Resultat(None, "erreur", f"prix_illisible:{valeur}")
    return Resultat(float(nombre), "corrige", "prix_texte_nettoye")


def parse_surface(valeur) -> Resultat:
    """Surface en m² -> float.

    Cas '1,250' (3 chiffres après la virgule) : lecture décimale (1,25) ou milliers (1 250) ?
    On retient la seule lecture comprise dans [SURFACE_ATYPIQUE_MIN, SURFACE_ATYPIQUE_MAX] ;
    si aucune ne l'est, le cas reste ambigu (aucune valeur devinée).
    Les nombres écrits en lettres ('quatre-vingt') ne sont pas convertis.
    """
    if est_vide(valeur):
        return Resultat(None, "absent", "surface_absente")
    if isinstance(valeur, bool):
        return Resultat(None, "erreur", "surface_booleenne")
    if isinstance(valeur, (int, float)):
        if isinstance(valeur, float) and not math.isfinite(valeur):
            return Resultat(None, "erreur", "surface_non_finie")
        return Resultat(float(valeur), "ok")

    brut = str(valeur).strip()
    if re.fullmatch(r"-?\d+(?:\.\d+)?", brut):
        return Resultat(float(brut), "ok")
    texte = re.sub(r"m\s?[²2]|m\u00b2|mètres?|metres?", "", brut.lower())
    nombre = _nettoyer(texte)
    if not re.match(r"^-?[\d.,]+$", nombre):
        return Resultat(None, "erreur", f"surface_non_numerique:{valeur}")

    if re.match(r"^-?\d{1,3},\d{3}$", nombre):
        decimale = float(nombre.replace(",", "."))
        milliers = float(nombre.replace(",", ""))
        bas, haut = settings.SURFACE_ATYPIQUE_MIN, settings.SURFACE_ATYPIQUE_MAX
        plausibles = [v for v in (decimale, milliers) if bas <= v <= haut]
        if len(plausibles) == 1:
            lecture = "decimale" if plausibles[0] == decimale else "milliers"
            return Resultat(plausibles[0], "corrige", f"surface_virgule_lue_{lecture}")
        return Resultat(None, "ambigu", f"surface_virgule_ambigue:{valeur}")

    nombre = nombre.replace(",", ".")
    if not _NOMBRE.match(nombre):
        return Resultat(None, "erreur", f"surface_illisible:{valeur}")
    return Resultat(float(nombre), "corrige", "surface_texte_nettoye")


def parse_entier(valeur, nom_champ: str = "entier") -> Resultat:
    """Chambres, salles de bain. 3, 3.0, '3' -> 3 ; 2.5 ou 'trois' -> erreur. Négatif conservé (validation)."""
    if est_vide(valeur):
        return Resultat(None, "absent", f"{nom_champ}_absent")
    if isinstance(valeur, str) and re.fullmatch(r"-?\d+", valeur.strip()):
        return Resultat(int(valeur.strip()), "ok")
    try:
        nombre = float(str(valeur).strip().replace(",", ".")) if isinstance(valeur, str) else float(valeur)
    except (TypeError, ValueError):
        return Resultat(None, "erreur", f"{nom_champ}_non_numerique:{valeur}")
    if not math.isfinite(nombre) or nombre != int(nombre):
        return Resultat(None, "erreur", f"{nom_champ}_non_entier:{valeur}")
    return Resultat(int(nombre), "ok" if isinstance(valeur, int) else "corrige",
                    None if isinstance(valeur, int) else f"{nom_champ}_converti_en_entier")


def prix_au_m2(prix: Optional[float], surface: Optional[float]) -> Optional[float]:
    """Prix/m² uniquement si les deux valeurs sont exploitables et strictement positives."""
    if prix is None or surface is None or prix <= 0 or surface <= 0:
        return None
    return prix / surface


def loyer_mensuel_equivalent(loyer: Optional[float], periodicite: Optional[str]) -> Optional[float]:
    """Ramène un loyer à son équivalent mensuel pour le comparer aux seuils. Périodicité inconnue -> None."""
    if loyer is None or periodicite not in settings.DIVISEUR_PERIODICITE:
        return None
    return loyer / settings.DIVISEUR_PERIODICITE[periodicite]
