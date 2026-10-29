"""Phase 5 : indicateurs de qualité (dénominateurs explicites, pas de double comptage, non évaluables à part)."""
import datetime as dt

import pytest

from src import pipeline
from src.processing import construire_bien
from src.validation import Validateur, rapport_qualite, rapport_vers_tableau
from tests.conftest_helpers import INDEX, NOTAIRES, PLATEFORME, REF, brut

INVENTAIRE = {"total_recus": 5, "sources": {
    "plateforme": {"lignes": 4, "valeurs_manquantes": {"montant": 1, "chambres": 4}, "colonnes_absentes_de_la_source": ["date_mise_a_jour"]},
    "notaires": {"lignes": 1, "valeurs_manquantes": {"montant": 0}, "colonnes_absentes_de_la_source": ["chambres"]}}}


def decisions():
    cas = [brut(), brut(montant="58.29 millions"), brut(montant="à négocier"), brut(surface="3000"),
           brut(type_transaction="location", periodicite=None)]
    biens = [construire_bien(c, PLATEFORME, INDEX) for c in cas]
    return Validateur(reference=REF).valider_lot(biens)


@pytest.fixture(scope="module")
def q():
    return rapport_qualite(decisions(), INVENTAIRE, [{"x": 1}], {"paires_conflit": 0}, REF)


def test_un_seul_statut_par_enregistrement(q):
    s = q["statuts_finaux"]
    assert s["evalues"] == 5
    assert s["quarantaine"] + s["conserves_avec_avertissement"] + s["entierement_conformes"] == 5
    assert (s["quarantaine"], s["entierement_conformes"]) == (1, 2) and s["controle_somme_ok"]
    assert s["taux_entierement_conformes_pct"] == 40.0          # 2 / 5 évalués


def test_corriges_sont_un_drapeau_transversal(q):
    assert q["statuts_finaux"]["corriges"] == 1                  # le prix en millions


def test_doublons_exacts_taux_sur_total_recu(q):
    v = q["volumes"]
    assert v["doublons_exacts"] == 1 and v["denominateur_taux_doublons"] == 5 and v["taux_doublons_exacts_pct"] == 20.0


def test_manquants_colonne_non_fournie_sort_du_denominateur(q):
    m = q["valeurs_manquantes_par_colonne"]
    assert m["montant"]["manquantes"] == 1 and m["montant"]["denominateur"] == 5 and m["montant"]["taux_pct"] == 20.0
    assert m["chambres"]["denominateur"] == 4 and m["chambres"]["sources_sans_la_colonne"] == ["notaires"]
    assert m["date_mise_a_jour"]["denominateur"] == 0 and m["date_mise_a_jour"]["taux_pct"] is None


def test_regles_non_evaluables_comptees_a_part(q):
    r = {x["regle"]: x for x in q["regles"]}
    assert r["loyer_positif"]["evaluables"] == 1 and r["loyer_positif"]["non_evaluables"] == 4
    assert r["prix_vente_positif"]["evaluables"] == 4 and r["prix_vente_positif"]["non_conformes"] == 1
    assert r["prix_vente_positif"]["taux_conformite"] == 75.0


def test_erreurs_de_conversion_par_champ_avec_denominateur(q):
    e = q["erreurs_conversion_par_champ"]["prix"]
    assert e["erreurs"] == 1 and e["denominateur"] == 5 and e["par_motif"] == {"prix_non_numerique": 1}


def test_motifs_et_ventes_locations_separees(q):
    assert q["motifs_quarantaine"] == {"prix_vente_positif": 1}
    assert "periodicite_valide" in q["motifs_avertissement"] and "surface_atypique" in q["motifs_avertissement"]
    assert q["volumes"]["ventes_evaluees"] == 4 and q["volumes"]["locations_evaluees"] == 1


def test_rappel_prix_demandes_present(q):
    assert "prix demandés" in q["avertissement_donnees"]


def test_tableau_a_plat_toutes_sections(q):
    t = rapport_vers_tableau(q)
    assert {"volumes", "statuts_finaux", "valeurs_manquantes", "erreurs_conversion", "regles"} <= {l["section"] for l in t}
    ligne = next(l for l in t if l["section"] == "regles" and l["indicateur"] == "prix_vente_positif")
    assert (ligne["valeur"], ligne["denominateur"], ligne["taux_pct"]) == (3, 4, 75.0)


def test_lot_vide():
    q0 = rapport_qualite([], {"total_recus": 0, "sources": {}}, [], {}, REF)
    assert q0["statuts_finaux"]["taux_entierement_conformes_pct"] is None and q0["regles"] == []


def test_rapport_reel_coherent_avec_bilan():
    res = pipeline.executer(reference=dt.date(2026, 10, 29), ecrire=False)
    s = res.qualite["statuts_finaux"]
    assert s["quarantaine"] == res.bilan["quarantaine"] and s["evalues"] == res.bilan["total_evalues"]
    somme_sources = sum(x["evalues"] for x in res.qualite["statuts_par_source"].values())
    assert somme_sources == s["evalues"]
