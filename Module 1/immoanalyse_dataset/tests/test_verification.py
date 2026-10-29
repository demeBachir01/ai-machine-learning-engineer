"""Phase 8 : contrôle d'intégrité des sources et cohérence des exports."""
import hashlib
import json

from src import pipeline
from src.verification import verifier_exports, verifier_sources, verifier_tout
import datetime as dt
from config import settings
import pytest


def test_sources_reelles_intactes():
    assert verifier_sources() == []


def test_modification_d_une_source_detectee(tmp_path):
    (tmp_path / "data" / "raw").mkdir(parents=True)
    f = tmp_path / "data" / "raw" / "a.csv"
    f.write_text("x;y\n1;2\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "checksums_sources.txt").write_text(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  raw/a.csv\n")
    assert verifier_sources(racine=tmp_path) == []
    f.write_text("x;y\n1;3\n", encoding="utf-8")                       # un seul caractère change
    assert verifier_sources(racine=tmp_path) == ["raw/a.csv"]
    f.unlink()                                                          # fichier supprimé = aussi une anomalie
    assert verifier_sources(racine=tmp_path) == ["raw/a.csv"]


@pytest.fixture()
def sorties(tmp_path, monkeypatch):
    for nom, d in (("PROCESSED_DIR", "p"), ("QUARANTINE_DIR", "q"), ("REPORTS_DIR", "r")):
        monkeypatch.setattr(settings, nom, tmp_path / d)
    return tmp_path, pipeline.executer(reference=dt.date(2026, 10, 29), ecrire=True)


def test_tous_les_controles_passent_sur_une_execution_complete(sorties):
    _, res = sorties
    controles = verifier_tout(res.bilan)
    assert len(controles) >= 14 and all(ok for _, ok, _ in controles), [c for c in controles if not c[1]]


def test_fichier_manquant_detecte(sorties):
    racine, res = sorties
    (racine / "q" / "quarantaine.json").unlink()
    c = verifier_exports(res.bilan)
    assert c[0][0] == "fichiers_attendus_presents" and not c[0][1] and "quarantaine.json" in c[0][2]


def test_incoherence_de_comptage_detectee(sorties):
    racine, res = sorties
    q = racine / "q" / "quarantaine.csv"
    lignes = q.read_text(encoding="utf-8-sig").splitlines()
    q.write_text("\n".join(lignes[:-1]) + "\n", encoding="utf-8-sig")          # une ligne perdue
    echecs = [n for n, ok, _ in verifier_exports(res.bilan) if not ok]
    assert "retenus + quarantaine + doublons exacts = reçu" in echecs


def test_quarantaine_sans_motif_detectee(sorties):
    import pandas as pd
    racine, res = sorties
    q = pd.read_csv(racine / "q" / "quarantaine.csv", encoding="utf-8-sig")
    q.loc[0, "motifs_quarantaine"] = None
    q.to_csv(racine / "q" / "quarantaine.csv", index=False, encoding="utf-8-sig")
    assert "chaque quarantaine a un motif" in [n for n, ok, _ in verifier_exports(res.bilan) if not ok]


def test_main_excel_facultatif(tmp_path, monkeypatch):
    from src.main import main
    for nom, d in (("PROCESSED_DIR", "p"), ("QUARANTINE_DIR", "q"), ("REPORTS_DIR", "r")):
        monkeypatch.setattr(settings, nom, tmp_path / d)
    assert main(["--date-reference", "2026-10-29", "--excel"]) == 0
    import openpyxl
    wb = openpyxl.load_workbook(tmp_path / "r" / "immo_analyse.xlsx", read_only=True)
    assert {"biens_dedupliques", "quarantaine", "quality_summary"} <= set(wb.sheetnames)
