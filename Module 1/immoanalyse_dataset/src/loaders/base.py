"""Interface commune des chargeurs. Phase 2 : le contrat ; phase 3 : une sous-classe par source."""
from abc import ABC, abstractmethod
from typing import Dict, List

import pandas as pd

from config import settings
from src.models import ContexteSource


class ChargeurSource(ABC):
    """Lit une source, renomme ses colonnes vers le schéma cible et ajoute la provenance.

    Une sous-classe définit seulement `contexte`, `mapping` et `lire()`.
    Les valeurs ne sont PAS converties ici : la conversion est le rôle de processing.normalisation.
    """
    contexte: ContexteSource
    mapping: Dict[str, str]           # colonne source -> colonne cible (voir settings.COLONNES_BRUTES_CIBLE)
    decalage_ligne: int = 2           # ligne du fichier = index + 2 (en-tête en ligne 1) ; 1 pour un JSON

    @abstractmethod
    def lire(self) -> pd.DataFrame:
        """Lit le fichier et retourne un DataFrame aux colonnes d'origine, en texte, sans modification."""

    def colonnes_non_mappees(self, df: pd.DataFrame) -> List[str]:
        return [c for c in df.columns if c not in self.mapping]

    def charger(self) -> List[dict]:
        df = self.lire()
        inconnues = set(self.mapping.values()) - set(settings.COLONNES_BRUTES_CIBLE)
        if inconnues:
            raise ValueError(f"{self.contexte.source} : colonnes cibles inconnues {sorted(inconnues)}")
        manquantes = [c for c in self.mapping if c not in df.columns]
        if manquantes:
            raise ValueError(f"{self.contexte.source} : colonnes attendues absentes {manquantes}")
        enregistrements = []
        for idx, ligne in zip(df.index, df.to_dict("records")):
            brut = {cible: None for cible in settings.COLONNES_BRUTES_CIBLE}
            for source, cible in self.mapping.items():
                valeur = ligne[source]
                brut[cible] = None if pd.isna(valeur) else valeur
            brut["ligne_origine"] = int(idx) + self.decalage_ligne
            enregistrements.append(brut)
        return enregistrements
