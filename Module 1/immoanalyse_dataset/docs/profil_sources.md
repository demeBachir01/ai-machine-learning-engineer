# Profil initial des 5 sources (phase 0)

Mesuré sur les fichiers réels de `data/raw/`. Les volumes sont ceux des fichiers, pas ceux du cahier des charges.

| Source | Lignes | Format | Particularités mesurées |
|---|---|---|---|
| plateforme_immo_sn.csv | 875 | `;` | 698 ventes / 177 locations ; périodicité dans `devise` (`FCFA/mois`) ; 15 lignes exactes en double (1,7 %) ; prix texte : 6 « à négocier », ~15 « xx.xx millions », 50 avec espaces ; 29 surfaces à virgule décimale ; 5 surfaces manquantes ; 5 dates futures ; `appart` (5) |
| agence_teranga.xlsx | 640 | feuille `Annonces` | **pas de `type_transaction`** ; feuille `Params` = métadonnées (version, date d'export), aucune donnée ; 5 prix à 0 ; 4 surfaces négatives (-30, -25, -30, -12) ; dates ISO (342) et JJ/MM/AAAA (298) |
| particuliers.json | 731 | liste de `{"annonce": {...}}` | 512 ventes / 219 locations, **sans périodicité** ; 61 prix manquants, 75 surfaces manquantes ; 7 prix texte (`65575000 FCFA`, `None FCFA`) ; 4 surfaces « quatre-vingt » ; 4 couples région/ville incohérents (Ziguinchor/Dakar) ; dates ISO et JJ/MM/AAAA |
| notaires.csv | 410 | `,` | 14 montants manquants ; 6 dates impossibles `32/13/2024` ; aucune transaction déclarée (actes de vente) |
| import_historique.csv | 528 | `;` latin-1 | 8 villes manquantes ; 10 prix manquants ; 72 prix avec espaces ; 50 surfaces à virgule décimale ; types en MAJUSCULES (152) ; 215 dates JJ/MM/AAAA |

## Constats transverses

- **Villes et régions** : toutes les valeurs non vides sont déjà dans le référentiel (aucun alias type « Dkr » trouvé). Les différences de casse/accents existent surtout sur `type_bien`.
- **Écart de volume** : la somme des fichiers est 3 184 lignes ; `fiche_conception_dataset.md` annonce 3 224 (agence : 680 annoncées, 640 trouvées). Écart de 40 lignes à signaler à l'encadrant.
- **Dates à barres** : dans agence, particuliers et historique, le 1er nombre dépasse 12 (181 / 269 / 127 cas) et le 2e ne le dépasse jamais. La convention est donc JJ/MM/AAAA.
- **Loyers sans périodicité** : seule la plateforme (via `devise`) la fournit. Agence (~106 locations déduites) et particuliers (219) n'en ont aucune.
- Le dossier `formateur/` cité par le README du pack n'est pas dans l'archive. Rien n'en dépend.
