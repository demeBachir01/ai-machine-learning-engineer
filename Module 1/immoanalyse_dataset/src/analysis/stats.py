"""Analyse NumPy / Pandas (phase 6) sur les biens dédupliqués (un enregistrement par id_bien).

Règles : ventes et locations ne sont JAMAIS mélangées ; un prix/m² n'existe que si prix et surface sont fiables ;
les prix de vente sont des prix demandés et les données sont synthétiques (à rappeler dans toute conclusion).
"""
from typing import Dict, Optional

import numpy as np
import pandas as pd

from config import settings

NOTE_DONNEES = ("Données synthétiques ; prix de vente = prix demandés (annonces), pas des transactions conclues : "
                "ces résultats décrivent le jeu de données, pas le marché.")


def charger_biens(chemin) -> pd.DataFrame:
    """Lit biens_dedupliques.csv avec les bons types (texte pour les champs libres, dates parsées)."""
    df = pd.read_csv(chemin, encoding="utf-8-sig", parse_dates=["date_collecte"])
    df["avertissements"] = df["avertissements"].fillna("")
    return df


def _sans_avertissement_exclu(df: pd.DataFrame) -> pd.Series:
    exclus = set(settings.AVERTISSEMENTS_EXCLUS_ANALYSE)
    return ~df["avertissements"].apply(lambda s: bool({m.split(" [")[0] for m in s.split(" | ") if m} & exclus))


def preparer(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les colonnes d'analyse sans modifier les données d'origine.

    - `fiable` : aucun avertissement d'atypie sur prix/surface/loyer et pas de conflit de prix.
    - `prix_m2_fiable` : ventes fiables uniquement ; `loyer_mensuel` : périodicité connue uniquement ;
      `loyer_m2_mensuel` : locations fiables uniquement.
    """
    d = df.copy()
    fiable = _sans_avertissement_exclu(d) & (d["statut_rapprochement"] != "conflit")
    d["fiable"] = fiable
    div = d["periodicite"].map(settings.DIVISEUR_PERIODICITE)
    d["loyer_mensuel"] = d["loyer"] / div
    vente = (d["type_transaction"] == "vente") & (d["prix"] > 0) & (d["surface"] > 0)
    loc = (d["type_transaction"] == "location") & (d["loyer_mensuel"] > 0) & (d["surface"] > 0)
    d["prix_m2_fiable"] = np.where(vente & fiable, d["prix"] / d["surface"], np.nan)
    d["loyer_m2_mensuel"] = np.where(loc & fiable, d["loyer_mensuel"] / d["surface"], np.nan)
    return d


def stats_descriptives(valeurs) -> Dict[str, Optional[float]]:
    """n, moyenne, écart-type (ddof=1), min, Q1, médiane, Q3, max — NaN ignorés, calcul NumPy."""
    a = np.asarray(pd.Series(valeurs).dropna(), dtype=float)
    if a.size == 0:
        return {k: None for k in ("n", "moyenne", "ecart_type", "min", "q1", "mediane", "q3", "max")} | {"n": 0}
    q1, med, q3 = np.percentile(a, [25, 50, 75])
    return {"n": int(a.size), "moyenne": float(a.mean()), "ecart_type": float(a.std(ddof=1)) if a.size > 1 else None,
            "min": float(a.min()), "q1": float(q1), "mediane": float(med), "q3": float(q3), "max": float(a.max())}


def tableau_descriptif(d: pd.DataFrame) -> pd.DataFrame:
    """Statistiques descriptives séparées ventes / locations, sur les données retenues."""
    lignes = []
    plan = {"vente": [("prix", "prix demandé (FCFA)"), ("surface", "surface (m²)"),
                      ("prix_m2_fiable", "prix/m² fiable (FCFA)")],
            "location": [("loyer_mensuel", "loyer mensuel équivalent (FCFA)"), ("surface", "surface (m²)"),
                         ("loyer_m2_mensuel", "loyer/m²/mois fiable (FCFA)")]}
    for transaction, colonnes in plan.items():
        sous = d[d["type_transaction"] == transaction]
        for col, libelle in colonnes:
            lignes.append({"transaction": transaction, "variable": libelle, **stats_descriptives(sous[col])})
    return pd.DataFrame(lignes)


def agreger(d: pd.DataFrame, transaction: str, par: str) -> pd.DataFrame:
    """Agrégation par ville / type_bien / source pour UNE transaction : effectifs, médianes, prix/m² fiable."""
    sous = d[d["type_transaction"] == transaction]
    montant, m2 = ("prix", "prix_m2_fiable") if transaction == "vente" else ("loyer_mensuel", "loyer_m2_mensuel")
    g = sous.groupby(par, dropna=False)
    out = pd.DataFrame({
        "n_biens": g.size(),
        f"{montant}_median": g[montant].median(),
        "surface_mediane": g["surface"].median(),
        "n_m2_fiables": g[m2].count(),
        f"{m2}_median": g[m2].median(),
        f"{m2}_moyenne": g[m2].mean(),
    }).reset_index()
    out["effectif_faible"] = out["n_biens"] < settings.ANALYSE_N_MIN_GROUPE
    return out.sort_values("n_biens", ascending=False).reset_index(drop=True)


def analyser(df: pd.DataFrame) -> dict:
    """Toutes les analyses de la phase 6, sous forme de DataFrames nommés + un résumé chiffré."""
    d = preparer(df)
    resultats = {"descriptif": tableau_descriptif(d)}
    for transaction in ("vente", "location"):
        for par in ("ville", "type_bien", "source"):
            resultats[f"{transaction}s_par_{par}"] = agreger(d, transaction, par)
    ventes, locs = d[d["type_transaction"] == "vente"], d[d["type_transaction"] == "location"]
    resume = {
        "note": NOTE_DONNEES,
        "biens_analyses": len(d), "ventes": len(ventes), "locations": len(locs),
        "ventes_avec_prix_m2_fiable": int(ventes["prix_m2_fiable"].notna().sum()),
        "ventes_exclues_du_prix_m2": int(ventes["prix_m2_fiable"].isna().sum()),
        "locations_avec_loyer_mensuel": int(locs["loyer_mensuel"].notna().sum()),
        "locations_sans_periodicite_exclues": int(locs["loyer_mensuel"].isna().sum()),
        "locations_avec_loyer_m2_fiable": int(locs["loyer_m2_mensuel"].notna().sum()),
        "biens_non_fiables": int((~d["fiable"]).sum()),
    }
    return {"donnees": d, "tables": resultats, "resume": resume}


def ecrire_analyse(analyse: dict, dossier) -> None:
    import json
    dossier.mkdir(parents=True, exist_ok=True)
    for nom, table in analyse["tables"].items():
        table.to_csv(dossier / f"analyse_{nom}.csv", index=False, encoding=settings.ENCODAGE_CSV)
    (dossier / "analyse_resume.json").write_text(json.dumps(analyse["resume"], ensure_ascii=False, indent=2),
                                                 encoding="utf-8")
