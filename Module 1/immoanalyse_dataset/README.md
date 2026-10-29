# ImmoAnalyse

Pipeline Python de contrôle qualité de données immobilières (5 sources, 3 formats). Projet fil rouge du Module 1.

## Installation
```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell : .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/verify_sources.py   # vérifie que data/raw et data/referentiels sont intacts
python -m pytest -q                # lance les tests
```

## État d'avancement
- [x] Phase 0 : squelette, sources figées (checksums), configuration, profil des sources, journal de décisions
- [x] Phase 1 : fonctions de base testées (`src/utils/`)
- [x] Phase 2 : modules, POO, règles de validation comme objets (`docs/architecture.md`)
- [ ] Phases 3 à 8

## Structure
- `config/settings.py` : tous les seuils, synonymes et conventions
- `src/models.py` : `Bien`, `Correction`, `ContexteSource`
- `src/loaders/` : contrat `ChargeurSource` (5 chargeurs en phase 3)
- `src/processing/` : `construire_bien` (brut -> `Bien` normalisé)
- `src/validation/` : règles, catalogue (`regles_metier.py`), `Validateur`, taux de conformité
- `src/utils/` : conversions (`numbers.py`, `dates.py`), normalisation (`text.py`), filtrage et avertissements (`biens.py`)
- `docs/decisions.md` : décisions justifiées ; `docs/profil_sources.md` : constats chiffrés
- `data/raw/`, `data/referentiels/` : **ne jamais modifier** (voir `docs/checksums_sources.txt`)

## Convention de résultat
Chaque conversion retourne `Resultat(valeur, statut, motif)` avec statut ∈ `ok | corrige | ambigu | erreur | absent`.
Un `absent` ou `ambigu` n'est jamais compté comme conforme.
