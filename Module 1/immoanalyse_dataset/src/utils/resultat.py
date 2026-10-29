"""Résultat standard d'une conversion/normalisation : on ne perd jamais la trace de ce qui s'est passé."""
from typing import Any, NamedTuple, Optional

# ok       : valeur déjà propre, rien changé
# corrige  : valeur convertie de façon fiable (la correction est documentée dans `motif`)
# ambigu   : plusieurs lectures possibles, on ne devine pas (valeur = None)
# erreur   : conversion impossible (valeur = None)
# absent   : valeur manquante (valeur = None)
STATUTS = ("ok", "corrige", "ambigu", "erreur", "absent")


class Resultat(NamedTuple):
    valeur: Any
    statut: str
    motif: Optional[str] = None

    @property
    def exploitable(self) -> bool:
        return self.statut in ("ok", "corrige")
