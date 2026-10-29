# ImmoAnalyse

Pipeline Python modulaire et reproductible qui transforme cinq sources immobilières hétérogènes (CSV, Excel, JSON) en
données contrôlées, accompagnées d'indicateurs de qualité chiffrés et d'une analyse. Projet fil rouge du Module 1.

> **Les données sont synthétiques et les prix de vente sont des prix demandés (annonces), pas des transactions conclues.**
> Les résultats décrivent ce jeu de données, pas le marché.

## 1. Installation
Python 3.10 ou plus récent.
```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell : .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/verify_sources.py   # vérifie que data/raw et data/referentiels sont intacts
python -m pytest -q                # lance les tests (environ 270)
```

## 2. Exécution
Un seul point d'entrée, à lancer depuis la racine du projet :
```bash
python -m src.main                              # date de référence = aujourd'hui
python -m src.main --date-reference 2026-10-29  # résultat reproductible
python -m src.main --excel                      # écrit aussi reports/immo_analyse.xlsx (facultatif)
```
Il exécute : chargement, normalisation, validation, doublons, rapport de qualité, analyse, puis 15 contrôles
(sources intactes, nombre de lignes cohérent entre fichiers, JSON = CSV...). Code de retour 0 si tout est OK.

Notebook : après `python -m src.main`, ouvrir `notebooks/01_exploration.ipynb` (`jupyter notebook`) et faire
*Run All*. Il lit les fichiers produits et s'exécute de haut en bas.

## 3. Sorties
| Fichier | Contenu |
|---|---|
| `data/processed/brut_unifie.csv` | Les 5 sources dans le schéma cible, valeurs brutes + provenance |
| `data/processed/biens_retenus.csv` / `.json` | Enregistrements conformes ou conservés avec avertissement (`id_bien`, avertissements, rapprochement) |
| `data/processed/biens_dedupliques.csv` / `.json` | Un enregistrement par `id_bien` ; base de l'analyse |
| `data/quarantine/quarantaine.csv` / `.json` | Enregistrements écartés, avec `motifs_quarantaine` et valeurs brutes |
| `data/processed/journal_corrections.csv` | Chaque correction et chaque inférence, avec ancienne et nouvelle valeur |
| `data/processed/doublons_exacts_ecartes.csv` | Doublons exacts écartés et ligne répétée |
| `data/processed/rapprochements.csv` | Paires de doublons probables et de conflits |
| `reports/quality_report.json` / `quality_summary.csv` | Indicateurs de qualité (dénominateurs explicites) |
| `reports/inventaire_anomalies.json` / `.csv` | Inventaire initial des anomalies par source |
| `reports/analyse_*.csv`, `analyse_resume.json` | Statistiques descriptives et agrégations (ventes et locations séparées) |
| `reports/bilan_traitement.json` | Comptes par source |
| `reports/immo_analyse.xlsx` | Export Excel facultatif (`--excel`) |

Les fichiers de `data/processed`, `data/quarantine` et `reports` sont régénérés à chaque exécution (non versionnés).

## 4. Règles métier
Chaque règle est un objet testable (`src/validation/regles_metier.py`) ; tous les seuils sont dans `config/settings.py`.

| Règle | Action |
|---|---|
| identifiant local présent, type de transaction valide, prix de vente > 0, loyer > 0, surface > 0 | quarantaine |
| date de collecte interprétable et non future, type de bien dans les 7 catégories | quarantaine |
| périodicité reconnue (jamais devinée), mise à jour >= collecte, région/ville cohérentes, chambres/salles de bain entiers >= 0 | avertissement |
| surface hors [5 ; 2 000] m², prix hors [100 000 ; 2 Md] FCFA, hors fourchette du type, prix/m² hors fourchette, loyer mensuel hors [25 000 ; 5 000 000], > 10 chambres (appartement/studio), salles de bain > chambres + 2 | avertissement |

Pour chaque règle, trois statuts : conforme, non conforme, **non évaluable** (compté à part, jamais conforme par défaut).
Taux de conformité d'une règle = conformes / évaluables.

**Un seul statut final par enregistrement** : doublon exact écarté, quarantaine, conservé avec avertissement ou
entièrement conforme. Taux global = entièrement conformes / évalués (reçus moins doublons exacts).

## 5. Résultats (date de référence 2026-10-29)
- 3 184 lignes reçues ; 15 doublons exacts écartés (0,47 %), tous dans la plateforme ; 3 169 évalués.
- 2 405 entièrement conformes (75,9 %), 574 conservés avec avertissement, 190 en quarantaine (6,0 %).
  Quarantaine par source : particuliers 136, notaires 20, plateforme 15, historique 10, agence 9.
- 1 375 enregistrements corrigés (dates, prix en millions, casse, synonymes...) ; 1 576 valeurs inférées (type de transaction
  pour les notaires, l'historique et l'agence). Tout est dans `journal_corrections.csv`.
- Rapprochement : 2 979 biens uniques, 0 doublon probable, 7 paires en conflit de prix (non fusionnées).
- Analyse : prix/m² fiable sur 2 434 ventes ; loyer mensuel sur 171 locations sur 449 (seule la plateforme indique la périodicité).

## 6. Décisions et limites
Toutes les décisions sont justifiées dans `docs/decisions.md` (37 entrées, dont celles de ne pas corriger). À retenir :
- **Rapprochement** sur ville + type + surface (±1 %) + date (±30 jours) + montant (±5 %), jamais sur les identifiants.
  Priorité de fusion : notaires > agence > plateforme > particuliers > historique. Un conflit n'est jamais fusionné.
- **Périodicité absente** : jamais devinée (décision 10, **à confirmer avec l'encadrant**) ; 325 loyers sont conservés avec avertissement.
- **Dates à barres** lues JJ/MM/AAAA, convention prouvée par les données (décision 7).
- **Seuils de plausibilité** : hypothèses pédagogiques ; `chambre_avec_plusieurs_chambres` et `sdb_superieures_chambres_plus_marge`
  signalent chacune environ 4 % des enregistrements (décision 24).
- **Écart de volume** : 3 184 lignes dans les fichiers contre 3 224 annoncées dans la fiche de conception (agence : 640 au lieu de 680).
- Hors périmètre : API, base de données, interface graphique, apprentissage automatique.

## 7. Structure
- `config/settings.py` : seuils, synonymes, tolérances de rapprochement, conventions
- `src/models.py` : `Bien`, `Correction`, `ContexteSource`
- `src/loaders/` : contrat `ChargeurSource`, 5 chargeurs (`sources.py`), inventaire (`inventaire.py`)
- `src/processing/` : `construire_bien`, doublons et fusion (`doublons.py`), exports (`export.py`)
- `src/validation/` : règles, catalogue, `Validateur`, indicateurs de qualité (`qualite.py`)
- `src/analysis/` : statistiques NumPy/Pandas (`stats.py`)
- `src/pipeline.py`, `src/verification.py`, `src/main.py` : orchestration, contrôles finaux, point d'entrée
- `src/utils/` : conversions et normalisation
- `notebooks/01_exploration.ipynb`, `tests/`, `docs/`, `scripts/verify_sources.py`
- `data/raw/`, `data/referentiels/` : **ne jamais modifier** (SHA-256 dans `docs/checksums_sources.txt`)

## 8. Test 
Dans un dossier vierge : suivre les sections 1 et 2, puis vérifier que `python -m pytest -q` est vert, que `python -m src.main`
affiche 15 contrôles `[OK]`, et que le notebook s'exécute avec *Run All* sans erreur.
