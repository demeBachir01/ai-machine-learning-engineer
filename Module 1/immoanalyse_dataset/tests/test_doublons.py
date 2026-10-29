import datetime as dt

from src.models import Bien
from src.processing.doublons import (CONFLIT, DOUBLON_PROBABLE, fusionner_groupe, ordre_priorite, rapprocher,
                                     separer_doublons_exacts)


def vente(source="notaires", id_local="A", prix=50_000_000.0, surface=100.0, date=dt.date(2024, 5, 1),
          ville="Thiès", type_bien="Maison", ligne=2, **kw):
    return Bien(source=source, id_local=id_local, ligne_origine=ligne, type_transaction="vente", type_bien=type_bien,
                ville=ville, prix=prix, surface=surface, date_collecte=date, **kw)


def location(source="agence", loyer=250_000.0, periodicite="mensuel", **kw):
    b = vente(source=source, **kw)
    b.type_transaction, b.prix, b.loyer, b.periodicite = "location", None, loyer, periodicite
    return b


# ---------------- doublons exacts
def test_doublon_exact_ignore_la_ligne_et_garde_la_premiere():
    a = {"id_local": "P1", "montant": "10", "ligne_origine": 2}
    b = {"id_local": "P1", "montant": "10", "ligne_origine": 9}
    c = {"id_local": "P1", "montant": "11", "ligne_origine": 10}      # même id, valeur différente : PAS un doublon exact
    uniques, doublons = separer_doublons_exacts([a, b, c])
    assert [u["ligne_origine"] for u in uniques] == [2, 10]
    assert doublons[0]["ligne_origine"] == 9 and doublons[0]["doublon_de_ligne"] == 2


def test_doublon_exact_distingue_les_types_de_valeur_brute():
    uniques, doublons = separer_doublons_exacts([{"m": 10, "ligne_origine": 2}, {"m": "10", "ligne_origine": 3}])
    assert len(uniques) == 2 and doublons == []


def test_aucun_doublon_exact():
    assert separer_doublons_exacts([]) == ([], [])


# ---------------- rapprochement
def test_doublon_probable_entre_sources_meme_id_bien_sans_utiliser_l_identifiant():
    a = vente("notaires", "NOT-1")
    b = vente("plateforme", "PLT-9", prix=51_000_000.0, surface=100.5, date=dt.date(2024, 5, 15))
    r = rapprocher([a, b])
    assert r.id_bien[0] == r.id_bien[1]
    assert r.statut == {0: DOUBLON_PROBABLE, 1: DOUBLON_PROBABLE}
    assert r.paires[0]["lien"] == DOUBLON_PROBABLE and r.paires[0]["ecart_jours"] == 14


def test_meme_identifiant_mais_attributs_differents_ne_rapproche_pas():
    r = rapprocher([vente(id_local="X", ville="Thiès"), vente(source="agence", id_local="X", ville="Mbour")])
    assert r.id_bien[0] != r.id_bien[1] and r.paires == []


def test_conflit_meme_bien_prix_contradictoires_pas_de_fusion():
    r = rapprocher([vente("notaires"), vente("plateforme", id_local="B", prix=80_000_000.0)])
    assert r.id_bien[0] != r.id_bien[1]
    assert r.statut == {0: CONFLIT, 1: CONFLIT} and r.paires[0]["lien"] == CONFLIT


def test_limites_des_tolerances():
    base = vente()
    assert rapprocher([base, vente(source="agence", date=dt.date(2024, 5, 31))]).statut[0] == DOUBLON_PROBABLE   # 30 j
    assert rapprocher([base, vente(source="agence", date=dt.date(2024, 6, 1))]).paires == []                       # 31 j
    assert rapprocher([base, vente(source="agence", surface=101.0)]).statut[0] == DOUBLON_PROBABLE                 # 1 %
    assert rapprocher([base, vente(source="agence", surface=102.0)]).paires == []                                  # 2 %
    assert rapprocher([base, vente(source="agence", prix=52_500_000.0)]).statut[0] == DOUBLON_PROBABLE            # 5 %
    assert rapprocher([base, vente(source="agence", prix=53_000_000.0)]).statut[0] == CONFLIT


def test_type_ou_ville_differents_jamais_rapproches():
    base = vente()
    assert rapprocher([base, vente(source="agence", type_bien="Villa")]).paires == []
    assert rapprocher([base, vente(source="agence", ville="Mbour")]).paires == []


def test_vente_et_location_jamais_comparees():
    r = rapprocher([vente(prix=250_000.0), location(loyer=250_000.0)])
    assert r.paires == [] and r.id_bien[0] != r.id_bien[1]


def test_locations_comparees_en_equivalent_mensuel():
    r = rapprocher([location("agence", 100_000.0, "mensuel"), location("plateforme", 1_200_000.0, "annuel")])
    assert r.statut[0] == DOUBLON_PROBABLE


def test_periodicite_inconnue_non_evaluable_aucune_hypothese():
    r = rapprocher([location("agence", 100_000.0, None), location("plateforme", 100_000.0, "mensuel")])
    assert r.paires == [] and r.paires_montant_non_evaluable == 1


def test_attributs_manquants_non_rapprochables():
    r = rapprocher([vente(ville=None), vente(source="agence", surface=None), vente(source="historique", date=None)])
    assert r.non_rapprochables == 3 and r.paires == []
    assert len(set(r.id_bien.values())) == 3                      # chacun reçoit son propre id_bien


def test_chaine_de_doublons_forme_un_seul_groupe_et_ids_deterministes():
    a, b, c = vente("notaires"), vente("agence", id_local="B"), vente("plateforme", id_local="C")
    r1, r2 = rapprocher([a, b, c]), rapprocher([a, b, c])
    assert len(set(r1.id_bien.values())) == 1 and r1.id_bien == r2.id_bien
    assert r1.id_bien[0] == "BIEN-00001"


def test_liste_vide():
    r = rapprocher([])
    assert r.id_bien == {} and r.paires == [] and r.groupes() == {}


# ---------------- fusion
def test_fusion_maitre_prioritaire_et_completion_sans_ecrasement():
    notaire = vente("notaires", prix=50_000_000.0, chambres=None, quartier=None)
    plateforme = vente("plateforme", id_local="P", prix=50_500_000.0, chambres=3, quartier="Nord")
    historique = vente("historique", id_local="H", chambres=9, salles_bain=2)
    maitre, completes, sources = fusionner_groupe([historique, plateforme, notaire])
    assert maitre.source == "notaires" and maitre.prix == 50_000_000.0          # valeur du maître jamais écrasée
    assert maitre.chambres == 3 and maitre.quartier == "Nord" and maitre.salles_bain == 2
    assert "chambres<-plateforme" in completes and "salles_bain<-historique" in completes
    assert sources == ["notaires", "plateforme", "historique"]
    assert notaire.chambres is None                                             # l'objet d'origine n'est pas modifié


def test_priorite_des_sources_puis_date_la_plus_recente():
    anciens = vente("agence", date=dt.date(2020, 1, 1))
    recent = vente("agence", date=dt.date(2024, 1, 1), ligne=3)
    assert sorted([anciens, recent, vente("notaires")], key=ordre_priorite)[0].source == "notaires"
    assert sorted([anciens, recent], key=ordre_priorite)[0] is recent


def test_groupe_d_un_seul_membre_est_renvoye_tel_quel():
    seul = vente()
    maitre, completes, sources = fusionner_groupe([seul])
    assert maitre is seul and completes == [] and sources == ["notaires"]
