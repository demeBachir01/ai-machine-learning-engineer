import datetime as dt

from src.processing import construire_bien
from src.validation import (AVERTISSEMENT, CONFORME, QUARANTAINE, RegleValidation, Action, Validateur,
                            synthese_globale, synthese_par_regle)
from tests.conftest_helpers import INDEX, PLATEFORME, REF, brut


def decider(**kw):
    return Validateur(reference=REF).valider(construire_bien(brut(**kw), PLATEFORME, INDEX))


def test_bien_entierement_conforme():
    d = decider()
    assert d.statut_final == CONFORME and d.motifs_quarantaine == [] and d.motifs_avertissement == []


def test_quarantaine_avec_motifs_et_detail():
    d = decider(montant="à négocier", surface="-30")
    assert d.statut_final == QUARANTAINE
    assert any(m.startswith("prix_vente_positif [prix_non_numerique") for m in d.motifs_quarantaine)
    assert "surface_positive" in d.motifs_quarantaine


def test_avertissement_ne_met_pas_en_quarantaine():
    d = decider(region="Ziguinchor", ville="Dakar")          # cas réel : couple incohérent
    assert d.statut_final == AVERTISSEMENT and d.motifs_avertissement == ["region_ville_coherentes"]


def test_quarantaine_prime_sur_avertissement():
    d = decider(region="Ziguinchor", ville="Dakar", date_collecte="2030-01-01")
    assert d.statut_final == QUARANTAINE


def test_regle_personnalisee_injectable():
    toujours_non = RegleValidation("test", "id_local", Action.QUARANTAINE, "x", lambda b: True, lambda b: False)
    d = Validateur(regles=[toujours_non], reference=REF).valider(construire_bien(brut(), PLATEFORME, INDEX))
    assert d.statut_final == QUARANTAINE and d.motifs_quarantaine == ["test"]


def _lot():
    v = Validateur(reference=REF)
    lot = [brut(), brut(montant="0"), brut(type_transaction="location", montant="250000", periodicite="/mois"),
           brut(region="Ziguinchor", ville="Dakar"), brut(ville=None)]
    return v.valider_lot(construire_bien(b, PLATEFORME, INDEX) for b in lot)


def test_synthese_globale_sans_double_comptage():
    s = synthese_globale(_lot())
    assert s["total_recus"] == 5 and s["controle_somme_ok"]
    assert s["quarantaine"] == 1                                   # montant 0
    assert s["quarantaine"] + s["conserves_avec_avertissement"] + s["entierement_conformes"] == 5


def test_taux_par_regle_denominateur_et_non_evaluables():
    lignes = {l["regle"]: l for l in synthese_par_regle(_lot())}
    prix = lignes["prix_vente_positif"]
    assert (prix["recus"], prix["evaluables"], prix["conformes"], prix["non_evaluables"]) == (5, 4, 3, 1)
    assert prix["taux_conformite"] == 75.0                          # 3 / 4 évaluables, pas 3 / 5
    geo = lignes["region_ville_coherentes"]
    assert geo["non_evaluables"] == 1 and geo["evaluables"] == 4    # ville absente : non évaluable, pas conforme
    assert lignes["loyer_positif"]["evaluables"] == 1


def test_taux_none_si_aucun_evaluable():
    lignes = {l["regle"]: l for l in synthese_par_regle(_lot())}
    assert lignes["date_mise_a_jour_coherente"]["taux_conformite"] is None


def test_lot_vide():
    assert synthese_par_regle([]) == []
    assert synthese_globale([])["taux_entierement_conformes"] is None


def test_inference_comptee_a_part_des_corrections():
    from tests.conftest_helpers import NOTAIRES
    v = Validateur(reference=REF)
    d = v.valider_lot([construire_bien(brut(type_transaction=None), NOTAIRES, INDEX),
                       construire_bien(brut(montant="58.29 millions"), PLATEFORME, INDEX)])
    s = synthese_globale(d)
    assert s["corriges"] == 1 and s["avec_valeur_inferee"] == 1
