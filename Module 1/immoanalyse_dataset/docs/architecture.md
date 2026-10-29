# Architecture (phase 2)

Chaque module a une seule responsabilité. Le flux de données va toujours de gauche à droite.

```
 loaders/            processing/              validation/                (phases 4-5)
 ChargeurSource  ->  construire_bien()   ->   Validateur.valider()   ->  export, rapport
 (lire, renommer,    (convertir, normaliser,  (appliquer les règles,
  provenance)         tracer corrections)      décider du statut)
      dict brut            Bien                    DecisionBien
```

| Module | Rôle | Ce qu'il NE fait PAS |
|---|---|---|
| `config/settings.py` | Seuils, synonymes, conventions par source | Aucune logique |
| `src/utils/` | Fonctions pures : `parse_*`, `normaliser_*`, `verifier_atypies` | Ne connaît ni `Bien` ni les sources |
| `src/models.py` | `Bien`, `Correction`, `ContexteSource` | Aucune règle |
| `src/loaders/` | Lecture, renommage des colonnes, provenance | Aucune conversion de valeur |
| `src/processing/` | `construire_bien` : brut -> `Bien` | Ne décide jamais de la quarantaine |
| `src/validation/` | `RegleValidation`, catalogue, `Validateur`, taux | Ne modifie jamais un `Bien` |
| `src/loaders/sources.py` | 5 chargeurs, `charger_toutes_les_sources`, `dataframe_brut_unifie` | Aucune conversion de valeur |
| `src/loaders/inventaire.py` | Inventaire initial des anomalies (volumes, manquants, formats, doublons bruts) | Ne corrige ni ne supprime rien |
| `src/processing/doublons.py` | Doublons exacts, rapprochement (doublons probables, conflits), `id_bien`, fusion | Ne regarde jamais l'identifiant local |
| `src/processing/export.py` | Écriture CSV / JSON | Aucune règle |
| `src/pipeline.py` | Orchestre phases 3-4 et écrit les sorties | Aucune règle métier propre |
| `src/main.py` | Point d'entrée (`python -m src.main`) | |

## Classes

- **`Bien`** (dataclass) : un enregistrement au schéma cible, plus 4 champs de traçabilité hors export : `erreurs_conversion`, `corrections`, `inferences`, `valeurs_brutes`.
- **`RegleValidation`** (dataclass figée) : `nom`, `champ`, `action` (quarantaine ou avertissement), `est_evaluable`, `est_conforme`. Elle retourne un `ResultatRegle` au statut conforme, non conforme ou **non évaluable**.
- **`Validateur`** : applique la liste de règles. On peut lui injecter ses propres règles (tests).
- **`ChargeurSource`** (classe abstraite) : le contrat des 5 chargeurs de la phase 3.

## Définitions des indicateurs

- **Statut final** (exclusif, un seul par enregistrement) : `quarantaine` si au moins une règle bloquante est non conforme ; sinon `conserve_avec_avertissement` si au moins un avertissement ; sinon `conforme`. Total = somme des trois, vérifié par `controle_somme_ok`.
- **Taux de conformité d'une règle** = conformes / (conformes + non conformes). Les non évaluables sont comptés à part et sortent du dénominateur.
- **Corrigé** : une valeur reçue a été modifiée de façon fiable (journal `corrections`).
- **Valeur inférée** : une valeur absente de la source a été déduite (journal `inferences`). Ce n'est pas une correction.
- **Entièrement conforme** : aucune règle non conforme. Une règle non applicable (ex. loyer sur une vente) ne compte pas contre l'enregistrement.

## Flux des phases 3 et 4

```
5 chargeurs -> dédoublonnage exact -> construire_bien -> Validateur -> rapprocher (retenus seulement) -> sorties
 (dict bruts)   (écartés, tracés)     (normaliser)      (statut final)   (id_bien, doublons, conflits)
```

Catégories finales, exclusives : doublon exact écarté | quarantaine | conservé avec avertissement | entièrement conforme.
`retenus + quarantaine + doublons exacts écartés = total reçu` (vérifié par `controle_total_ok`).
