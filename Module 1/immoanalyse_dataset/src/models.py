"""Objets de données du pipeline : un bien normalisé, une correction tracée, le contexte d'une source."""
import datetime as dt
from dataclasses import dataclass, field, fields
from typing import Any, Optional

from src.utils.numbers import prix_au_m2


@dataclass(frozen=True)
class Correction:
    """Une modification fiable et documentée d'une valeur (journal des corrections)."""
    champ: str
    ancienne_valeur: Any
    nouvelle_valeur: Any
    motif: str


@dataclass(frozen=True)
class ContexteSource:
    """Ce que le pipeline sait d'une source ; tout est explicite, rien n'est deviné en silence."""
    source: str
    fichier: str
    convention_date: Optional[str] = "JJ/MM"
    transaction_par_defaut: Optional[str] = None     # ex. 'vente' pour les actes notariés (décision 9)
    inferer_transaction: bool = False                # True pour l'agence (décision 8)


_TRACE = ("erreurs_conversion", "corrections", "inferences", "valeurs_brutes")


@dataclass
class Bien:
    """Enregistrement normalisé (schéma cible). Une valeur manquante ou non convertible vaut None."""
    source: str
    fichier: str = ""
    ligne_origine: Optional[int] = None
    id_local: Optional[str] = None
    id_bien: Optional[str] = None                    # attribué après rapprochement (phase 4)
    type_transaction: Optional[str] = None
    type_bien: Optional[str] = None
    region: Optional[str] = None
    ville: Optional[str] = None
    quartier: Optional[str] = None
    prix: Optional[float] = None                     # ventes uniquement : prix DEMANDÉ
    loyer: Optional[float] = None                    # locations uniquement
    periodicite: Optional[str] = None
    surface: Optional[float] = None
    pieces: Optional[int] = None
    chambres: Optional[int] = None
    salles_bain: Optional[int] = None
    date_collecte: Optional[dt.date] = None
    date_mise_a_jour: Optional[dt.date] = None
    statut: Optional[str] = None
    geo_coherent: Optional[bool] = None              # None = non évaluable
    # --- traçabilité (hors export des données propres) ---
    erreurs_conversion: dict = field(default_factory=dict)   # champ -> motif
    corrections: list = field(default_factory=list)          # list[Correction] : valeur reçue ET modifiée
    inferences: dict = field(default_factory=dict)           # champ -> motif : valeur ABSENTE de la source, déduite
    valeurs_brutes: dict = field(default_factory=dict)       # valeurs reçues avant tout traitement

    @property
    def est_infere(self) -> bool:
        return bool(self.inferences)

    @property
    def est_corrige(self) -> bool:
        return bool(self.corrections)

    @property
    def prix_m2(self) -> Optional[float]:
        """Prix au m² des VENTES uniquement ; un loyer n'est jamais rapporté à la surface ici."""
        return prix_au_m2(self.prix, self.surface) if self.type_transaction == "vente" else None

    def vers_dict(self) -> dict:
        """Champs métier uniquement (sans la traçabilité), pour l'export et les contrôles."""
        return {f.name: getattr(self, f.name) for f in fields(self) if f.name not in _TRACE}
