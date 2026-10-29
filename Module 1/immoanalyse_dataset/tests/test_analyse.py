"""Phase 6 : statistiques NumPy/Pandas, prix au m² fiables, séparation ventes / locations."""
import numpy as np
import pandas as pd
import pytest

from src.analysis import agreger, analyser, preparer, stats_descriptives, tableau_descriptif


def bien(**kw):
    base = {"type_transaction": "vente", "type_bien": "Maison", "ville": "Thiès", "source": "notaires", "prix": 50e6,
            "loyer": np.nan, "periodicite": np.nan, "surface": 100.0, "avertissements": "", "statut_rapprochement": "unique"}
    base.update(kw)
    return base


def df(*lignes):
    return pd.DataFrame(lignes)


def test_stats_descriptives_valeurs_connues():
    s = stats_descriptives([1, 2, 3, 4, 5])
    assert (s["n"], s["moyenne"], s["mediane"], s["q1"], s["q3"], s["min"], s["max"]) == (5, 3.0, 3.0, 2.0, 4.0, 1.0, 5.0)
    assert s["ecart_type"] == pytest.approx(np.std([1, 2, 3, 4, 5], ddof=1))


def test_stats_ignorent_les_nan_et_gerent_vide_et_singleton():
    assert stats_descriptives([1, np.nan, 3])["n"] == 2
    assert stats_descriptives([np.nan]) ["n"] == 0 and stats_descriptives([])["moyenne"] is None
    assert stats_descriptives([7])["ecart_type"] is None and stats_descriptives([7])["mediane"] == 7.0


def test_prix_m2_calcule_pour_une_vente_fiable():
    d = preparer(df(bien()))
    assert d["prix_m2_fiable"].iloc[0] == 500_000 and bool(d["fiable"].iloc[0])


@pytest.mark.parametrize("avert", ["prix_atypique", "surface_atypique", "prix_hors_fourchette_type",
                                   "prix_m2_hors_fourchette_type", "surface_hors_fourchette_type",
                                   "chambres_atypiques | prix_atypique"])
def test_prix_m2_exclu_si_valeur_atypique(avert):
    assert np.isnan(preparer(df(bien(avertissements=avert)))["prix_m2_fiable"].iloc[0])


def test_avertissement_sans_rapport_avec_prix_et_surface_n_exclut_pas():
    assert preparer(df(bien(avertissements="periodicite_valide | chambres_atypiques")))["prix_m2_fiable"].iloc[0] == 500_000


def test_prix_m2_exclu_en_cas_de_conflit_de_prix():
    assert np.isnan(preparer(df(bien(statut_rapprochement="conflit")))["prix_m2_fiable"].iloc[0])


def test_surface_nulle_ou_prix_manquant_jamais_de_prix_m2():
    d = preparer(df(bien(surface=0.0), bien(prix=np.nan)))
    assert d["prix_m2_fiable"].isna().all()


def test_loyer_annuel_converti_en_mensuel_et_periodicite_inconnue_exclue():
    d = preparer(df(bien(type_transaction="location", prix=np.nan, loyer=1_200_000.0, periodicite="annuel"),
                    bien(type_transaction="location", prix=np.nan, loyer=250_000.0, periodicite=np.nan)))
    assert d["loyer_mensuel"].iloc[0] == 100_000 and d["loyer_m2_mensuel"].iloc[0] == 1_000
    assert np.isnan(d["loyer_mensuel"].iloc[1]) and np.isnan(d["loyer_m2_mensuel"].iloc[1])


def test_une_location_n_a_jamais_de_prix_m2_ni_une_vente_de_loyer_m2():
    d = preparer(df(bien(), bien(type_transaction="location", prix=np.nan, loyer=100_000.0, periodicite="mensuel")))
    assert np.isnan(d["prix_m2_fiable"].iloc[1]) and np.isnan(d["loyer_m2_mensuel"].iloc[0])


def test_agregation_par_transaction_et_effectif_faible():
    d = preparer(df(bien(), bien(prix=70e6), bien(type_bien="Villa", prix=200e6, surface=200.0),
                    bien(type_transaction="location", prix=np.nan, loyer=100_000.0, periodicite="mensuel")))
    a = agreger(d, "vente", "type_bien").set_index("type_bien")
    assert a.loc["Maison", "n_biens"] == 2 and a.loc["Maison", "prix_median"] == 60e6
    assert bool(a.loc["Villa", "effectif_faible"]) and "Villa" in a.index
    assert agreger(d, "location", "type_bien")["n_biens"].sum() == 1       # la location n'entre pas dans les ventes


def test_tableau_descriptif_separe_ventes_et_locations():
    d = preparer(df(bien(), bien(type_transaction="location", prix=np.nan, loyer=100_000.0, periodicite="mensuel")))
    t = tableau_descriptif(d)
    assert set(t["transaction"]) == {"vente", "location"}
    assert t.query("transaction == 'vente' and variable.str.startswith('prix demandé')")["n"].iloc[0] == 1


def test_analyse_complete_resume_et_note():
    a = analyser(df(bien(), bien(type_transaction="location", prix=np.nan, loyer=1.0e5, periodicite=np.nan)))
    r = a["resume"]
    assert (r["ventes"], r["locations"], r["locations_sans_periodicite_exclues"]) == (1, 1, 1)
    assert "prix demandés" in r["note"]
    assert "ventes_par_ville" in a["tables"] and "locations_par_source" in a["tables"]


def test_analyse_sur_fichiers_reels_ecrits_par_le_pipeline():
    from src import pipeline
    from src.analysis import charger_biens
    import datetime as dt
    res = pipeline.executer(reference=dt.date(2026, 10, 29), ecrire=False)
    d = analyser(pd.DataFrame(res.dedupliques).assign(
        avertissements=lambda x: x["avertissements"].fillna("")))
    assert d["resume"]["ventes"] + d["resume"]["locations"] == len(res.dedupliques)
    assert d["resume"]["ventes_avec_prix_m2_fiable"] > 2000
