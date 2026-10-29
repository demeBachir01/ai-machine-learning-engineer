"""Phases 3-4 de bout en bout sur les vraies sources : cohérence des comptes, des exports et de la quarantaine."""
import datetime as dt
import json

import pandas as pd
import pytest

from config import settings
from src import pipeline
from src.main import main

REF = dt.date(2026, 10, 29)


@pytest.fixture(scope="module")
def res():
    return pipeline.executer(reference=REF, ecrire=False)


def test_comptes_coherents_sans_double_comptage(res):
    b = res.bilan
    assert b["total_recus"] == 3184 and b["doublons_exacts_ecartes"] == 15
    assert b["retenus"] + b["quarantaine"] + b["doublons_exacts_ecartes"] == b["total_recus"]
    assert b["controle_total_ok"]
    assert b["quarantaine"] + b["conserves_avec_avertissement"] + b["entierement_conformes"] == b["total_evalues"]
    assert sum(s["recus"] for s in b["par_source"].values()) == 3184
    assert b["taux_doublons_exacts_pct"] == round(100 * 15 / 3184, 2)


def test_anomalies_attendues_en_quarantaine(res):
    motifs = " ".join(m for d in res.quarantaine for m in d.motifs_quarantaine)
    for attendu in ("date_impossible:32/13/2024", "prix_non_numerique:à négocier", "surface_non_numerique:quatre-vingt",
                    "date_collecte_non_future", "prix_non_numerique:None FCFA", "transaction_non_deductible"):
        assert attendu in motifs, attendu


def test_chaque_enregistrement_en_quarantaine_a_un_motif_et_aucun_retenu_n_en_a(res):
    assert all(d.motifs_quarantaine for d in res.quarantaine)
    assert not any(d.motifs_quarantaine for d in res.retenus)


def test_retenus_sont_exploitables(res):
    for d in res.retenus:
        b = d.bien
        assert b.id_local and b.surface and b.surface > 0 and b.date_collecte <= REF
        assert b.type_bien in settings.TYPES_BIEN and b.type_transaction in settings.TYPES_TRANSACTION
        assert (b.prix > 0) if b.type_transaction == "vente" else (b.loyer > 0)
        assert (b.loyer is None) if b.type_transaction == "vente" else (b.prix is None)    # jamais mélangés


def test_aucune_periodicite_inventee(res):
    sans = [d.bien for d in res.retenus if d.bien.type_transaction == "location" and d.bien.periodicite is None]
    assert sans and all("periodicite_valide" in " ".join(d.motifs_avertissement)
                        for d in res.retenus if d.bien in sans)


def test_id_bien_attribue_a_tous_les_retenus_et_dedupliques_uniques(res):
    assert all(d.bien.id_bien for d in res.retenus)
    ids = [l["id_bien"] for l in res.dedupliques]
    assert len(ids) == len(set(ids)) == res.bilan["rapprochement"]["biens_uniques_apres_rapprochement"]
    assert sum(l["nb_enregistrements"] for l in res.dedupliques) == len(res.retenus)


def test_aucun_conflit_ne_fusionne_deux_enregistrements(res):
    for p in res.rapprochement.paires:
        if p["lien"] == "conflit":
            assert p["ecart_montant_pct"] > settings.DOUBLON_MONTANT_TOLERANCE * 100
    assert res.bilan["rapprochement"]["paires_conflit"] == 7


def test_pipeline_deterministe(res):
    autre = pipeline.executer(reference=REF, ecrire=False)
    assert autre.bilan == res.bilan
    assert [l["id_bien"] for l in autre.dedupliques[:50]] == [l["id_bien"] for l in res.dedupliques[:50]]


def test_sources_brutes_intactes(res):
    assert res.bilan["sources_intactes"] is True


def test_date_reference_modifie_la_regle_date_future():
    plus_tot = pipeline.executer(reference=dt.date(2019, 1, 1), ecrire=False)
    assert plus_tot.bilan["quarantaine"] > 190


@pytest.fixture()
def sorties(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "PROCESSED_DIR", tmp_path / "processed")
    monkeypatch.setattr(settings, "QUARANTINE_DIR", tmp_path / "quarantine")
    monkeypatch.setattr(settings, "REPORTS_DIR", tmp_path / "reports")
    return tmp_path, pipeline.executer(reference=REF, ecrire=True)


def test_exports_lisibles_et_coherents(sorties):
    racine, res = sorties
    lire = lambda p: pd.read_csv(racine / p, encoding="utf-8-sig")
    retenus, quar = lire("processed/biens_retenus.csv"), lire("quarantine/quarantaine.csv")
    doublons, dedup = lire("processed/doublons_exacts_ecartes.csv"), lire("processed/biens_dedupliques.csv")
    assert len(retenus) + len(quar) + len(doublons) == 3184
    assert len(lire("processed/brut_unifie.csv")) == 3184
    assert len(dedup) == res.bilan["rapprochement"]["biens_uniques_apres_rapprochement"]
    assert quar["motifs_quarantaine"].notna().all()
    assert retenus["id_bien"].notna().all() and set(retenus["source"]) <= set(settings.PRIORITE_SOURCES)
    assert "Thiès" in set(retenus["ville"])                                    # accents préservés
    texte = pd.read_csv(racine / "processed/biens_retenus.csv", encoding="utf-8-sig", dtype=str)
    assert not texte["chambres"].dropna().str.contains(r"\.").any()                # entiers écrits sans '.0'


def test_exports_json_equivalents_au_csv(sorties):
    racine, res = sorties
    retenus = json.loads((racine / "processed/biens_retenus.json").read_text(encoding="utf-8"))
    quar = json.loads((racine / "quarantine/quarantaine.json").read_text(encoding="utf-8"))
    assert len(retenus) == len(res.retenus) and len(quar) == len(res.quarantaine)
    assert isinstance(retenus[0]["date_collecte"], str) and retenus[0]["loyer"] is None or retenus[0]["prix"]


def test_journal_des_corrections_distingue_corrections_et_inferences(sorties):
    racine, res = sorties
    j = pd.read_csv(racine / "processed/journal_corrections.csv", encoding="utf-8-sig")
    assert set(j["nature"]) == {"correction", "inference"}
    assert (j["nature"] == "correction").sum() == sum(len(d.bien.corrections) for d in res.decisions)
    assert j["motif"].notna().all()
    assert "prix_millions_converti" in set(j["motif"])


def test_rapports_phase3_et_bilan_ecrits(sorties):
    racine, _ = sorties
    inv = json.loads((racine / "reports/inventaire_anomalies.json").read_text(encoding="utf-8"))
    bilan = json.loads((racine / "reports/bilan_traitement.json").read_text(encoding="utf-8"))
    assert inv["total_recus"] == 3184 and bilan["controle_total_ok"]
    assert (racine / "reports/inventaire_anomalies.csv").exists()


def test_main_retourne_zero(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(settings, "PROCESSED_DIR", tmp_path / "p")
    monkeypatch.setattr(settings, "QUARANTINE_DIR", tmp_path / "q")
    monkeypatch.setattr(settings, "REPORTS_DIR", tmp_path / "r")
    assert main(["--date-reference", "2026-10-29"]) == 0
    sortie = capsys.readouterr().out
    assert "[OK] retenus + quarantaine + doublons exacts = reçu" in sortie and "ÉCHEC" not in sortie
