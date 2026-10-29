"""Catalogue des règles métier (cahier §6.1 et §6.2). Tous les seuils viennent de config.settings."""
import datetime as dt
from typing import Callable, List

from config import settings
from src.models import Bien
from src.utils import loyer_mensuel_equivalent, prix_au_m2, verifier_atypies
from .regle import Action, RegleValidation

Q, A = Action.QUARANTAINE, Action.AVERTISSEMENT


def _toujours(_: Bien) -> bool:
    return True


def _est(transaction: str) -> Callable[[Bien], bool]:
    return lambda b: b.type_transaction == transaction


def _regle_atypie(code: str, champ: str, description: str, evaluable: Callable[[Bien], bool]) -> RegleValidation:
    """Les seuils vivent à UN seul endroit : utils.biens.verifier_atypies. Ici on isole chaque code
    pour obtenir un taux de conformité par règle, avec son propre dénominateur."""
    return RegleValidation(code, champ, A, description, evaluable,
                           lambda b: code not in verifier_atypies(b.vers_dict()))


def _champ_entier_valide(champ: str) -> RegleValidation:
    return RegleValidation(
        f"{champ}_entier_positif_ou_nul", champ, A, f"{champ} : entier >= 0",
        lambda b: getattr(b, champ) is not None or champ in b.erreurs_conversion,
        lambda b: getattr(b, champ) is not None and getattr(b, champ) >= 0)


def construire_regles(reference: dt.date) -> List[RegleValidation]:
    """Retourne la liste ordonnée des règles. `reference` = date d'exécution (pour 'date non future')."""
    return [
        # ---- bloquantes (quarantaine) ----
        RegleValidation("id_local_present", "id_local", Q, "Identifiant local obligatoire",
                        _toujours, lambda b: b.id_local is not None),
        RegleValidation("type_transaction_valide", "type_transaction", Q, "vente ou location après normalisation",
                        _toujours, lambda b: b.type_transaction in settings.TYPES_TRANSACTION),
        RegleValidation("prix_vente_positif", "prix", Q, "Prix de vente numérique strictement positif",
                        _est("vente"), lambda b: b.prix is not None and b.prix > 0),
        RegleValidation("loyer_positif", "loyer", Q, "Loyer numérique strictement positif",
                        _est("location"), lambda b: b.loyer is not None and b.loyer > 0),
        RegleValidation("surface_positive", "surface", Q, "Surface numérique strictement positive",
                        _toujours, lambda b: b.surface is not None and b.surface > 0),
        RegleValidation("date_collecte_valide", "date_collecte", Q, "Date interprétable",
                        _toujours, lambda b: b.date_collecte is not None),
        RegleValidation("date_collecte_non_future", "date_collecte", Q, "Date non postérieure à la date d'exécution",
                        lambda b: b.date_collecte is not None, lambda b: b.date_collecte <= reference),
        RegleValidation("type_bien_valide", "type_bien", Q, "Type dans les 7 catégories (décision 1)",
                        _toujours, lambda b: b.type_bien in settings.TYPES_BIEN),
        # ---- avertissements ----
        RegleValidation("periodicite_valide", "periodicite", A, "Périodicité du loyer reconnue (jamais devinée)",
                        _est("location"), lambda b: b.periodicite in settings.PERIODICITES),
        RegleValidation("date_mise_a_jour_coherente", "date_mise_a_jour", A, "Mise à jour >= collecte",
                        lambda b: b.date_mise_a_jour is not None and b.date_collecte is not None,
                        lambda b: b.date_mise_a_jour >= b.date_collecte),
        RegleValidation("region_ville_coherentes", "ville", A, "Couple région/ville présent au référentiel",
                        lambda b: b.geo_coherent is not None, lambda b: b.geo_coherent is True),
        _champ_entier_valide("chambres"),
        _champ_entier_valide("salles_bain"),
        # ---- atypies (avertissement, jamais suppression) ----
        _regle_atypie("surface_atypique", "surface", "Surface hors [5 ; 2000] m²",
                      lambda b: b.surface is not None and b.surface > 0),
        _regle_atypie("surface_hors_fourchette_type", "surface", "Surface hors fourchette typique du type",
                      lambda b: b.surface is not None and b.surface > 0 and b.type_bien in settings.FOURCHETTES),
        _regle_atypie("prix_atypique", "prix", "Prix de vente hors [100 000 ; 2 Md] FCFA",
                      lambda b: b.type_transaction == "vente" and b.prix is not None and b.prix > 0),
        _regle_atypie("prix_hors_fourchette_type", "prix", "Prix hors fourchette indicative du type",
                      lambda b: b.type_transaction == "vente" and b.prix is not None and b.prix > 0
                      and b.type_bien in settings.FOURCHETTES),
        _regle_atypie("prix_m2_hors_fourchette_type", "prix", "Prix/m² hors fourchette (option A, décision 6)",
                      lambda b: b.prix_m2 is not None and b.type_bien in settings.FOURCHETTES),
        _regle_atypie("loyer_atypique", "loyer", "Loyer mensuel équivalent hors [25 000 ; 5 000 000]",
                      lambda b: b.type_transaction == "location" and b.loyer is not None and b.loyer > 0
                      and loyer_mensuel_equivalent(b.loyer, b.periodicite) is not None),
        _regle_atypie("chambres_atypiques", "chambres", "Plus de 10 chambres pour un appartement/studio",
                      lambda b: b.chambres is not None and b.type_bien in settings.TYPES_BIEN_CHAMBRES_CONTROLEES),
        _regle_atypie("sdb_superieures_chambres_plus_marge", "salles_bain", "Salles de bain > chambres + 2",
                      lambda b: b.chambres is not None and b.salles_bain is not None),
        _regle_atypie("terrain_avec_pieces", "chambres", "Terrain avec chambres ou salles de bain (décision 20)",
                      lambda b: b.type_bien == "Terrain" and (b.chambres is not None or b.salles_bain is not None)),
        _regle_atypie("chambre_avec_plusieurs_chambres", "chambres", "Type 'Chambre' avec plus d'une chambre (décision 20)",
                      lambda b: b.type_bien == "Chambre" and b.chambres is not None),
    ]
