"""Écriture des sorties (CSV et JSON). Dates en ISO, nombres entiers sans '.0', jamais de NaN."""
import datetime as dt
import json
from pathlib import Path
from typing import Iterable, List

import pandas as pd

from config import settings


def nettoyer(valeur):
    """Valeur prête à écrire : None pour le vide, date ISO, entier si le flottant est entier."""
    if valeur is None or (isinstance(valeur, float) and valeur != valeur):
        return None
    if isinstance(valeur, (dt.date, dt.datetime)):
        return valeur.isoformat()
    if isinstance(valeur, float):
        return int(valeur) if valeur == int(valeur) else round(valeur, 2)
    return valeur


def ecrire_csv(lignes: List[dict], chemin: Path, colonnes: Iterable[str] = None) -> Path:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    propres = [{k: nettoyer(v) for k, v in l.items()} for l in lignes]
    df = pd.DataFrame(propres, columns=list(colonnes) if colonnes else None, dtype=object)
    df.to_csv(chemin, index=False, encoding=settings.ENCODAGE_CSV)
    return chemin


def ecrire_json(lignes: List[dict], chemin: Path) -> Path:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    propres = [{k: nettoyer(v) for k, v in l.items()} for l in lignes]
    chemin.write_text(json.dumps(propres, ensure_ascii=False, indent=2), encoding="utf-8")
    return chemin


def ecrire_objet_json(objet: dict, chemin: Path) -> Path:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(objet, ensure_ascii=False, indent=2, default=nettoyer), encoding="utf-8")
    return chemin


def ecrire_excel(chemin: Path, feuilles: dict) -> Path:
    """Export Excel facultatif : {nom de feuille: DataFrame}. Nécessite openpyxl (déjà dans requirements)."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(chemin, engine="openpyxl") as w:
        for nom, df in feuilles.items():
            df.to_excel(w, sheet_name=nom[:31], index=False)
            ws = w.sheets[nom[:31]]
            ws.freeze_panes = "A2"
            for col in ws.columns:
                largeur = max((len(str(c.value)) for c in list(col)[:200] if c.value is not None), default=8)
                ws.column_dimensions[col[0].column_letter].width = min(max(10, largeur + 2), 60)
    return chemin
