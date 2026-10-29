"""Doublons exacts, doublons probables, conflits, id_bien global et fusion (phase 4.3).

Principes : on ne rapproche JAMAIS sur l'identifiant local (non fiable) mais sur des attributs métier ;
ventes et locations ne sont jamais comparées entre elles ; en cas de doute on ne fusionne pas.
"""
import copy
import itertools
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from config import settings
from src.models import Bien
from src.utils import loyer_mensuel_equivalent

DOUBLON_PROBABLE, CONFLIT = "doublon_probable", "conflit"


# ------------------------------------------------------------------ doublons exacts
def separer_doublons_exacts(enregistrements: Sequence[dict]) -> Tuple[List[dict], List[dict]]:
    """(uniques, doublons) pour UNE source. Exact = toutes les valeurs brutes identiques, `ligne_origine`
    exceptée. La 1re occurrence est gardée ; chaque doublon écarté est tracé avec la ligne qu'il répète."""
    vus: Dict[tuple, int] = {}
    uniques, doublons = [], []
    for e in enregistrements:
        cle = tuple((k, repr(v)) for k, v in sorted(e.items()) if k != "ligne_origine")
        if cle in vus:
            doublons.append({**e, "doublon_de_ligne": vus[cle]})
        else:
            vus[cle] = e["ligne_origine"]
            uniques.append(e)
    return uniques, doublons


# ------------------------------------------------------------------ rapprochement
def montant_comparable(b: Bien) -> Tuple[Optional[float], Optional[str]]:
    """(montant, unité). Vente : prix. Location : loyer ramené au mois ; périodicité inconnue -> non comparable."""
    if b.type_transaction == "vente":
        return b.prix, "vente"
    if b.type_transaction == "location":
        return loyer_mensuel_equivalent(b.loyer, b.periodicite), "location_mensuel"
    return None, None


def _rapprochable(b: Bien) -> bool:
    return all(v is not None for v in (b.type_transaction, b.ville, b.type_bien, b.surface, b.date_collecte)) \
        and b.surface > 0


def _ecart_relatif(x: float, y: float) -> float:
    return abs(x - y) / max(abs(x), abs(y))


@dataclass
class Rapprochement:
    """Résultat : paires liées, groupes de doublons probables et id_bien attribué à chaque enregistrement."""
    paires: List[dict] = field(default_factory=list)            # doublons probables ET conflits, une ligne par paire
    id_bien: Dict[int, str] = field(default_factory=dict)       # position dans la liste -> id_bien
    statut: Dict[int, str] = field(default_factory=dict)        # position -> unique | doublon_probable | conflit
    non_rapprochables: int = 0                                  # attributs clés manquants
    paires_montant_non_evaluable: int = 0                       # périodicité inconnue : on ne devine pas

    def groupes(self) -> Dict[str, List[int]]:
        g: Dict[str, List[int]] = {}
        for pos, idb in self.id_bien.items():
            g.setdefault(idb, []).append(pos)
        return g


def _trouver(parent: List[int], i: int) -> int:
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def rapprocher(biens: Sequence[Bien]) -> Rapprochement:
    """Compare les biens (déjà ordonnés par priorité de source) à l'intérieur de blocs
    (transaction, ville, type) : surface proche, date proche, puis montant proche (doublon) ou éloigné (conflit)."""
    res = Rapprochement()
    parent = list(range(len(biens)))
    blocs: Dict[tuple, List[int]] = {}
    for i, b in enumerate(biens):
        if _rapprochable(b):
            blocs.setdefault((b.type_transaction, b.ville, b.type_bien), []).append(i)
        else:
            res.non_rapprochables += 1

    en_conflit = set()
    for cle, positions in blocs.items():
        for i, j in itertools.combinations(positions, 2):
            a, b = biens[i], biens[j]
            ecart_surface = _ecart_relatif(a.surface, b.surface)
            jours = abs((a.date_collecte - b.date_collecte).days)
            if ecart_surface > settings.DOUBLON_SURFACE_TOLERANCE or jours > settings.DOUBLON_JOURS_MAX:
                continue
            (ma, _), (mb, _) = montant_comparable(a), montant_comparable(b)
            if ma is None or mb is None or ma <= 0 or mb <= 0:
                res.paires_montant_non_evaluable += 1
                continue
            ecart_montant = _ecart_relatif(ma, mb)
            type_lien = DOUBLON_PROBABLE if ecart_montant <= settings.DOUBLON_MONTANT_TOLERANCE else CONFLIT
            if type_lien == DOUBLON_PROBABLE:
                parent[_trouver(parent, j)] = _trouver(parent, i)
            else:
                en_conflit.update((i, j))
            res.paires.append({
                "lien": type_lien, "transaction": a.type_transaction, "ville": a.ville, "type_bien": a.type_bien,
                "source_a": a.source, "id_local_a": a.id_local, "ligne_a": a.ligne_origine,
                "source_b": b.source, "id_local_b": b.id_local, "ligne_b": b.ligne_origine,
                "surface_a": a.surface, "surface_b": b.surface, "ecart_surface_pct": round(100 * ecart_surface, 2),
                "date_a": a.date_collecte.isoformat(), "date_b": b.date_collecte.isoformat(), "ecart_jours": jours,
                "montant_a": ma, "montant_b": mb, "ecart_montant_pct": round(100 * ecart_montant, 2),
            })

    # id_bien : un par composante de doublons probables, numéroté dans l'ordre de priorité des sources
    numeros: Dict[int, str] = {}
    taille: Dict[int, int] = {}
    for i in range(len(biens)):
        racine = _trouver(parent, i)
        taille[racine] = taille.get(racine, 0) + 1
        if racine not in numeros:
            numeros[racine] = f"{settings.PREFIXE_ID_BIEN}{len(numeros) + 1:05d}"
        res.id_bien[i] = numeros[racine]
    for i in range(len(biens)):
        if taille[_trouver(parent, i)] > 1:
            res.statut[i] = DOUBLON_PROBABLE
        elif i in en_conflit:
            res.statut[i] = CONFLIT
        else:
            res.statut[i] = "unique"
    # un bien à la fois doublon probable et en conflit garde la mention la plus alarmante
    for i in en_conflit:
        res.statut[i] = CONFLIT
    return res


# ------------------------------------------------------------------ fusion
def rang_source(source: str) -> int:
    return settings.PRIORITE_SOURCES.index(source) if source in settings.PRIORITE_SOURCES else len(settings.PRIORITE_SOURCES)


def ordre_priorite(b: Bien) -> tuple:
    """Source la plus fiable d'abord ; à source égale, la collecte la plus récente, puis la ligne la plus haute."""
    return (rang_source(b.source), -(b.date_collecte.toordinal() if b.date_collecte else 0), b.ligne_origine or 0)


def fusionner_groupe(membres: List[Bien]) -> Tuple[Bien, List[str], List[str]]:
    """(maître, champs complétés, sources membres). Le maître est le membre prioritaire ; ses champs vides sont
    remplis depuis les autres membres (même ordre de priorité). Aucune valeur renseignée n'est jamais écrasée."""
    tries = sorted(membres, key=ordre_priorite)
    maitre = tries[0]
    completes = []
    if len(tries) > 1:
        maitre = copy.copy(maitre)
        for champ in settings.CHAMPS_COMPLETABLES:
            if getattr(maitre, champ) is None:
                for autre in tries[1:]:
                    valeur = getattr(autre, champ)
                    if valeur is not None:
                        setattr(maitre, champ, valeur)
                        completes.append(f"{champ}<-{autre.source}")
                        break
    return maitre, completes, [m.source for m in tries]
