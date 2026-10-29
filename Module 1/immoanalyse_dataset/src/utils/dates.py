"""Lecture de dates multi-formats avec convention explicite par source."""
import datetime as dt
import re
from typing import Optional

from .resultat import Resultat
from .text import cle_texte, est_vide

MOIS = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7,
        "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12}
_ISO = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_BARRES = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_LETTRES = re.compile(r"^(\d{1,2})(?:er)? ([a-z]+) (\d{4})$")
_RELATIF = {"aujourd'hui": 0, "aujourdhui": 0, "hier": 1, "avant-hier": 2, "avant hier": 2}


def _construire(annee: int, mois: int, jour: int, motif_ok: Optional[str], statut: str) -> Resultat:
    try:
        return Resultat(dt.date(annee, mois, jour), statut, motif_ok)
    except ValueError:
        return Resultat(None, "erreur", f"date_impossible:{jour:02d}/{mois:02d}/{annee}")


def parse_date(valeur, convention: Optional[str] = "JJ/MM", reference: Optional[dt.date] = None) -> Resultat:
    """Date -> datetime.date.

    - ISO 'AAAA-MM-JJ' : sans ambiguïté.
    - 'JJ/MM/AAAA' ou 'MM/JJ/AAAA' : si un nombre dépasse 12, la lecture est certaine. Sinon on applique
      `convention` (documentée par source dans settings.CONVENTION_DATE) ; sans convention -> 'ambigu'.
    - '12 mars 2024', '1er février 2023' : mois en lettres.
    - 'hier', 'aujourd'hui' : relatifs à `reference` (date de collecte ou d'exécution).
    - Dates impossibles ('32/13/2024') -> erreur. Les dates futures sont une règle de validation, pas de parsing.
    """
    if est_vide(valeur):
        return Resultat(None, "absent", "date_absente")
    if isinstance(valeur, dt.datetime):
        return Resultat(valeur.date(), "ok")
    if isinstance(valeur, dt.date):
        return Resultat(valeur, "ok")

    texte = str(valeur).strip()
    m = _ISO.match(texte)
    if m:
        return _construire(int(m[1]), int(m[2]), int(m[3]), None, "ok")

    m = _BARRES.match(texte)
    if m:
        a, b, annee = int(m[1]), int(m[2]), int(m[3])
        if a > 12 and b > 12:
            return Resultat(None, "erreur", f"date_impossible:{texte}")
        if a > 12:
            return _construire(annee, b, a, "date_JJ/MM_certaine", "corrige")
        if b > 12:
            return _construire(annee, a, b, "date_MM/JJ_certaine", "corrige")
        if convention == "JJ/MM":
            return _construire(annee, b, a, "date_ambigue_resolue_par_convention_source_JJ/MM", "corrige")
        if convention == "MM/JJ":
            return _construire(annee, a, b, "date_ambigue_resolue_par_convention_source_MM/JJ", "corrige")
        return Resultat(None, "ambigu", f"date_ambigue:{texte}")

    cle = cle_texte(texte)
    if cle in _RELATIF:
        if reference is None:
            return Resultat(None, "ambigu", f"date_relative_sans_reference:{texte}")
        return Resultat(reference - dt.timedelta(days=_RELATIF[cle]), "corrige", "date_relative_resolue")

    m = _LETTRES.match(cle)
    if m and m[2] in MOIS:
        return _construire(int(m[3]), MOIS[m[2]], int(m[1]), "date_mois_en_lettres", "corrige")

    return Resultat(None, "erreur", f"date_illisible:{texte}")


def est_future(date: Optional[dt.date], reference: Optional[dt.date] = None) -> Optional[bool]:
    """True si la date est postérieure à la date de référence (par défaut : aujourd'hui). None si non évaluable."""
    if date is None:
        return None
    return date > (reference or dt.date.today())
