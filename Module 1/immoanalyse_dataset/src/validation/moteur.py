"""Moteur de validation : applique les règles, décide du statut final et calcule les taux de conformité."""
import datetime as dt
from dataclasses import dataclass
from typing import Iterable, List, Optional

from src.models import Bien
from .regle import Action, RegleValidation, ResultatRegle, StatutRegle
from .regles_metier import construire_regles

# Statut final : UNE seule catégorie par enregistrement (évite le double comptage, cahier §7)
QUARANTAINE, AVERTISSEMENT, CONFORME = "quarantaine", "conserve_avec_avertissement", "conforme"


@dataclass
class DecisionBien:
    bien: Bien
    resultats: List[ResultatRegle]

    def _non_conformes(self, action: Action) -> List[ResultatRegle]:
        return [r for r in self.resultats if r.statut == StatutRegle.NON_CONFORME and r.action == action]

    @property
    def motifs_quarantaine(self) -> List[str]:
        return [r.regle + (f" [{r.detail}]" if r.detail else "") for r in self._non_conformes(Action.QUARANTAINE)]

    @property
    def motifs_avertissement(self) -> List[str]:
        return [r.regle + (f" [{r.detail}]" if r.detail else "") for r in self._non_conformes(Action.AVERTISSEMENT)]

    @property
    def statut_final(self) -> str:
        if self.motifs_quarantaine:
            return QUARANTAINE
        return AVERTISSEMENT if self.motifs_avertissement else CONFORME


class Validateur:
    def __init__(self, regles: Optional[List[RegleValidation]] = None, reference: Optional[dt.date] = None):
        self.reference = reference or dt.date.today()
        self.regles = regles if regles is not None else construire_regles(self.reference)

    def valider(self, bien: Bien) -> DecisionBien:
        return DecisionBien(bien, [r.appliquer(bien) for r in self.regles])

    def valider_lot(self, biens: Iterable[Bien]) -> List[DecisionBien]:
        return [self.valider(b) for b in biens]


def synthese_par_regle(decisions: List[DecisionBien]) -> List[dict]:
    """Une ligne par règle. Dénominateur = enregistrements ÉVALUABLES ; les non évaluables sont comptés à part."""
    lignes = []
    noms = [(r.regle, r.action.value) for r in decisions[0].resultats] if decisions else []
    for i, (nom, action) in enumerate(noms):
        statuts = [d.resultats[i].statut for d in decisions]
        conformes = statuts.count(StatutRegle.CONFORME)
        non_conformes = statuts.count(StatutRegle.NON_CONFORME)
        evaluables = conformes + non_conformes
        lignes.append({
            "regle": nom, "action": action, "recus": len(decisions), "evaluables": evaluables,
            "conformes": conformes, "non_conformes": non_conformes,
            "non_evaluables": statuts.count(StatutRegle.NON_EVALUABLE),
            "taux_conformite": round(100 * conformes / evaluables, 2) if evaluables else None,
        })
    return lignes


def synthese_globale(decisions: List[DecisionBien]) -> dict:
    """Catégories finales mutuellement exclusives ; 'corriges' et 'avec_valeur_inferee' sont des drapeaux transversaux (non exclusifs)."""
    total = len(decisions)
    comptes = {QUARANTAINE: 0, AVERTISSEMENT: 0, CONFORME: 0}
    for d in decisions:
        comptes[d.statut_final] += 1
    corriges = sum(1 for d in decisions if d.bien.est_corrige)
    inferes = sum(1 for d in decisions if d.bien.est_infere)
    return {
        "total_recus": total,
        "quarantaine": comptes[QUARANTAINE],
        "conserves_avec_avertissement": comptes[AVERTISSEMENT],
        "entierement_conformes": comptes[CONFORME],
        "corriges": corriges,
        "avec_valeur_inferee": inferes,
        "taux_entierement_conformes": round(100 * comptes[CONFORME] / total, 2) if total else None,
        "controle_somme_ok": sum(comptes.values()) == total,
    }
