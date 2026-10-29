"""Contrôles finaux (phase 8) : sources intactes, exports lisibles et cohérents entre eux."""
import hashlib
import json
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

from config import settings

Controle = Tuple[str, bool, str]


def verifier_sources(fichier_checksums: Optional[Path] = None, racine: Optional[Path] = None) -> List[str]:
    """Retourne la liste des fichiers de data/ dont le SHA-256 diffère de docs/checksums_sources.txt (ou absents)."""
    racine = racine or settings.ROOT
    fichier_checksums = fichier_checksums or racine / "docs" / "checksums_sources.txt"
    modifies = []
    for ligne in fichier_checksums.read_text(encoding="utf-8").splitlines():
        if not ligne.strip():
            continue
        attendu, chemin = ligne.split(maxsplit=1)
        cible = racine / "data" / chemin.strip().lstrip("*")
        if not cible.exists() or hashlib.sha256(cible.read_bytes()).hexdigest() != attendu:
            modifies.append(chemin.strip())
    return modifies


def _csv(chemin: Path) -> pd.DataFrame:
    return pd.read_csv(chemin, encoding=settings.ENCODAGE_CSV, dtype=str)


def verifier_exports(bilan: dict, processed: Optional[Path] = None, quarantine: Optional[Path] = None,
                     reports: Optional[Path] = None) -> List[Controle]:
    """Vérifie que les fichiers produits existent, se relisent, et se recoupent (nombre de lignes, identifiants)."""
    processed = processed or settings.PROCESSED_DIR
    quarantine = quarantine or settings.QUARANTINE_DIR
    reports = reports or settings.REPORTS_DIR
    controles: List[Controle] = []

    def ajouter(nom, ok, detail=""):
        controles.append((nom, bool(ok), detail))

    attendus = [processed / n for n in ("brut_unifie.csv", "biens_retenus.csv", "biens_retenus.json",
                                        "biens_dedupliques.csv", "biens_dedupliques.json", "journal_corrections.csv",
                                        "rapprochements.csv", "doublons_exacts_ecartes.csv")]
    attendus += [quarantine / "quarantaine.csv", quarantine / "quarantaine.json"]
    attendus += [reports / n for n in ("quality_report.json", "quality_summary.csv", "inventaire_anomalies.json",
                                       "inventaire_anomalies.csv", "bilan_traitement.json", "analyse_resume.json")]
    absents = [p.name for p in attendus if not p.exists()]
    ajouter("fichiers_attendus_presents", not absents, ", ".join(absents))
    if absents:
        return controles

    retenus, quar = _csv(processed / "biens_retenus.csv"), _csv(quarantine / "quarantaine.csv")
    doublons, brut = _csv(processed / "doublons_exacts_ecartes.csv"), _csv(processed / "brut_unifie.csv")
    dedup = _csv(processed / "biens_dedupliques.csv")
    total = bilan["total_recus"]
    ajouter("brut_unifie = total reçu", len(brut) == total, f"{len(brut)} / {total}")
    ajouter("retenus + quarantaine + doublons exacts = reçu", len(retenus) + len(quar) + len(doublons) == total,
            f"{len(retenus)} + {len(quar)} + {len(doublons)} / {total}")
    ajouter("dedupliques = biens uniques du bilan", len(dedup) == bilan["rapprochement"]["biens_uniques_apres_rapprochement"])
    ajouter("id_bien unique dans les dédupliqués", dedup["id_bien"].is_unique and dedup["id_bien"].notna().all())
    ajouter("chaque quarantaine a un motif", quar["motifs_quarantaine"].notna().all())
    ajouter("aucun retenu n'est en quarantaine", set(retenus["statut_validation"]) <= {"conforme", "conserve_avec_avertissement"})
    cles_retenus = set(zip(retenus["source"], retenus["ligne_origine"]))
    cles_quar = set(zip(quar["source"], quar["ligne_origine"]))
    ajouter("aucun enregistrement à la fois retenu et en quarantaine", not (cles_retenus & cles_quar))

    for nom, csv, chemin_json in (("retenus", retenus, processed / "biens_retenus.json"),
                                  ("dédupliqués", dedup, processed / "biens_dedupliques.json"),
                                  ("quarantaine", quar, quarantine / "quarantaine.json")):
        donnees = json.loads(chemin_json.read_text(encoding="utf-8"))
        ajouter(f"JSON {nom} = CSV ({len(csv)} lignes)", len(donnees) == len(csv), f"{len(donnees)} / {len(csv)}")
    rapport = json.loads((reports / "quality_report.json").read_text(encoding="utf-8"))
    s = rapport["statuts_finaux"]
    ajouter("rapport qualité : statuts = évalués", s["quarantaine"] + s["conserves_avec_avertissement"] +
            s["entierement_conformes"] == s["evalues"] and s["controle_somme_ok"])
    ajouter("rapport qualité : quarantaine = fichier", s["quarantaine"] == len(quar))
    resume = _csv(reports / "quality_summary.csv")
    ajouter("quality_summary.csv non vide", len(resume) > 0)
    return controles


def verifier_tout(bilan: dict) -> List[Controle]:
    modifies = verifier_sources()
    controles = [("sources et référentiels intacts (SHA-256)", not modifies, ", ".join(modifies))]
    return controles + verifier_exports(bilan)
