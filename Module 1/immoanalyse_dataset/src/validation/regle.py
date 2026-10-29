"""Classe de base d'une règle de validation et de son résultat.

Une règle est un OBJET (nom, champ, action, deux prédicats) : elle est donc testable isolément,
listable dans le rapport de qualité et configurable sans toucher au moteur.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from src.models import Bien


class Action(str, Enum):
    QUARANTAINE = "quarantaine"       # règle bloquante
    AVERTISSEMENT = "avertissement"   # on conserve et on signale


class StatutRegle(str, Enum):
    CONFORME = "conforme"
    NON_CONFORME = "non_conforme"
    NON_EVALUABLE = "non_evaluable"   # jamais compté comme conforme (cahier §7)


@dataclass(frozen=True)
class ResultatRegle:
    regle: str
    action: Action
    statut: StatutRegle
    detail: Optional[str] = None      # ex. motif de conversion : 'prix_non_numerique:à négocier'


@dataclass(frozen=True)
class RegleValidation:
    nom: str                                      # code stable, utilisé comme motif dans les exports
    champ: str                                    # champ principal contrôlé
    action: Action
    description: str
    est_evaluable: Callable[[Bien], bool]         # la règle s'applique-t-elle à ce bien ?
    est_conforme: Callable[[Bien], bool]          # appelée seulement si évaluable

    def appliquer(self, bien: Bien) -> ResultatRegle:
        if not self.est_evaluable(bien):
            return ResultatRegle(self.nom, self.action, StatutRegle.NON_EVALUABLE)
        if self.est_conforme(bien):
            return ResultatRegle(self.nom, self.action, StatutRegle.CONFORME)
        return ResultatRegle(self.nom, self.action, StatutRegle.NON_CONFORME,
                             detail=bien.erreurs_conversion.get(self.champ))
