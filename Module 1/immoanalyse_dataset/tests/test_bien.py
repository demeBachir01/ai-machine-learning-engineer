from src.models import Bien, Correction
from tests.conftest_helpers import AGENCE, INDEX, NOTAIRES, PLATEFORME, brut
from src.processing import construire_bien


def test_vers_dict_exclut_la_tracabilite():
    d = Bien(source="x", prix=1.0).vers_dict()
    assert "inferences" not in d
    assert "corrections" not in d and "erreurs_conversion" not in d and "valeurs_brutes" not in d
    assert d["prix"] == 1.0 and d["source"] == "x"


def test_prix_m2_seulement_pour_les_ventes():
    assert Bien(source="x", type_transaction="vente", prix=60_000_000, surface=100).prix_m2 == 600_000
    assert Bien(source="x", type_transaction="location", loyer=300_000, surface=100).prix_m2 is None
    assert Bien(source="x", type_transaction="vente", prix=None, surface=100).prix_m2 is None


def test_vente_valide_sans_correction():
    b = construire_bien(brut(), PLATEFORME, INDEX)
    assert (b.type_transaction, b.prix, b.surface, b.chambres) == ("vente", 60_581_000.0, 90.5, 2)
    assert b.corrections == [] and b.erreurs_conversion == {} and b.geo_coherent is True and b.loyer is None


def test_location_loyer_et_periodicite_jamais_melanges_avec_prix():
    b = construire_bien(brut(type_transaction="location", montant="250 000", periodicite="FCFA/mois"), PLATEFORME, INDEX)
    assert b.loyer == 250_000.0 and b.prix is None and b.periodicite == "mensuel"


def test_location_sans_periodicite_non_devinee():
    b = construire_bien(brut(type_transaction="location", montant="250000"), PLATEFORME, INDEX)
    assert b.periodicite is None and "periodicite" not in b.erreurs_conversion


def test_prix_en_millions_corrige_et_trace():
    b = construire_bien(brut(montant="58.29 millions"), PLATEFORME, INDEX)
    assert b.prix == 58_290_000.0
    assert Correction("prix", "58.29 millions", 58_290_000.0, "prix_millions_converti") in b.corrections


def test_prix_illisible_aucune_valeur_devinee():
    b = construire_bien(brut(montant="à négocier"), PLATEFORME, INDEX)
    assert b.prix is None and "prix" in b.erreurs_conversion


def test_transaction_inconnue_le_montant_nest_pas_traite():
    b = construire_bien(brut(type_transaction=None, montant="60581000"), PLATEFORME, INDEX)
    assert b.type_transaction is None and b.prix is None and b.loyer is None


def test_agence_transaction_inferee_et_tracee():
    b = construire_bien(brut(type_transaction=None, montant="450000", statut="Loué"), AGENCE, INDEX)
    assert b.type_transaction == "location" and b.loyer == 450_000.0
    assert "statut_loue" in b.inferences["type_transaction"]
    assert b.corrections == [] and b.est_infere and not b.est_corrige      # inférence != correction


def test_agence_montant_zero_non_deductible():
    b = construire_bien(brut(type_transaction=None, montant="0", statut="Disponible"), AGENCE, INDEX)
    assert b.type_transaction is None and "type_transaction" in b.erreurs_conversion


def test_notaires_vente_par_defaut():
    b = construire_bien(brut(type_transaction=None), NOTAIRES, INDEX)
    assert b.type_transaction == "vente"
    assert b.inferences["type_transaction"] == "transaction_par_defaut_de_la_source" and not b.est_corrige


def test_date_impossible_et_date_jj_mm():
    assert construire_bien(brut(date_collecte="32/13/2024"), NOTAIRES, INDEX).erreurs_conversion["date_collecte"]
    b = construire_bien(brut(date_collecte="05/06/2018"), NOTAIRES, INDEX)
    assert str(b.date_collecte) == "2018-06-05"


def test_localisation_incoherente_conservee():
    b = construire_bien(brut(region="Ziguinchor", ville="Dakar"), PLATEFORME, INDEX)
    assert (b.region, b.ville, b.geo_coherent) == ("Ziguinchor", "Dakar", False)


def test_surface_en_lettres_et_valeurs_brutes_conservees():
    b = construire_bien(brut(surface="quatre-vingt"), PLATEFORME, INDEX)
    assert b.surface is None and b.valeurs_brutes["surface"] == "quatre-vingt"


def test_type_bien_normalise_et_inconnu():
    assert construire_bien(brut(type_bien="APPART"), PLATEFORME, INDEX).type_bien == "Appartement"
    b = construire_bien(brut(type_bien="château"), PLATEFORME, INDEX)
    assert b.type_bien is None and "type_bien" in b.erreurs_conversion
