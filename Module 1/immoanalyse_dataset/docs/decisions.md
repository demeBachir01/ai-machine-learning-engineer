# Journal de décisions

Statut : **proposée** = à valider en équipe avant la phase 4. Chaque décision précise sa preuve.

| # | Sujet | Décision | Justification / preuve | Statut |
|---|---|---|---|---|
| 1 | Type de bien hors référentiel | Quarantaine | Le cahier (§6.1) dit quarantaine, `regles_metier.md` dit avertissement. Le type pilote toutes les analyses par catégorie. Aucun cas réel hors synonymes dans les sources. | proposée |
| 2 | Virgule dans une surface (« 1,250 ») | On retient la seule lecture dans [5 ; 2 000] m² ; sinon ambigu, aucune valeur devinée | Une surface de 1,25 m² est invraisemblable, 1 250 m² plausible (cahier §6.3). Aucun cas à 3 décimales dans les sources : la règle est testée en unitaire. | proposée |
| 3 | Virgule dans un prix | Séparateur de milliers ; décimale seulement avec « millions » explicite ; « 1.250 » = ambigu | `regles_metier.md` ; « 58.29 millions » observé. | proposée |
| 4 | Date future | Quarantaine pour toute `date_collecte` future ; `date_expiration` non contrôlée | Cahier §6.1. 5 dates futures dans la plateforme. Une expiration future est normale. | proposée |
| 5 | Doublon probable | Groupe commun, aucune suppression sans règle de priorité documentée | `regles_metier.md` : ne pas fusionner sans justification. | proposée |
| 6 | Prix au m² hors fourchette | Option A : [prix_min / surface_max ; prix_max / surface_min] du type | Le référentiel ne fournit pas de fourchette de prix/m². L'option B (stricte) signalerait beaucoup de faux positifs. | proposée |
| 7 | Convention des dates à barres | JJ/MM/AAAA pour toutes les sources, appliquée même si les deux nombres sont ≤ 12 | Preuve : 1er nombre > 12 dans 577 cas, 2e nombre jamais. Date `motif` = `convention_source`. | proposée |
| 8 | `type_transaction` de l'agence | Inféré : Loué → location ; Vendu / En vente → vente ; Disponible → selon montant (< 2 M = location) ; sinon ambigu | Mesuré : tous les montants < 2 M sont Loué/Disponible, tous les ≥ 2 M Vendu/En vente. Toujours marqué `corrige` avec motif. | proposée |
| 9 | `type_transaction` notaires et historique | `vente` (niveau source) | Actes notariés (tous Vendu / Vente conclue / Acte signé) et colonne `DateVente`. À consigner dans la colonne de provenance. | proposée |
| 10 | Périodicité manquante | Jamais devinée. Loyer sans périodicité : conservé avec avertissement, seuils de loyer non évaluables | Cahier §6.1 « ne pas deviner ». Concerne agence et particuliers (~325 locations). **À confirmer avec l'encadrant** : l'hypothèse « mensuel » est probable mais non prouvée. | à arbitrer |
| 11 | `pieces` (plateforme) | Colonne distincte, non assimilée à `chambres` | Un nombre de pièces inclut le séjour. | proposée |
| 12 | Surfaces négatives (4 agence) | Non corrigées (pas de changement de signe) → quarantaine | Règle bloquante surface ≤ 0 ; aucune preuve que le signe est la seule erreur. | proposée |
| 13 | Prix = 0 (5 agence) et prix manquants | Quarantaine | Règle bloquante prix ≤ 0 ou absent. | proposée |
| 14 | « quatre-vingt » (4 particuliers) | Non converti → erreur → quarantaine | Un nombre écrit en lettres est ambigu (80 ? 4×20 ?) et incomplet. | proposée |
| 15 | Région/ville incohérentes (4 particuliers) | Avertissement, valeurs conservées | Cahier : ne pas corriger sans preuve. | proposée |
| 16 | Ville absente (8 historique) | Avertissement ; la région ne permet pas de déduire la ville | Plusieurs villes par région. | proposée |
| 17 | Région absente, ville unique au référentiel | Région déduite et tracée (`region_deduite_de_la_ville`) | Preuve : la ville n'existe que dans une région. | proposée |
| 18 | Coordonnées du référentiel géo | Non utilisées | Identiques pour toutes les villes d'une même région. | proposée |
| 19 | Feuille `Params` de l'Excel | Ignorée comme donnée ; `Version` et `Date_export` conservées pour la provenance | Aucune annonce dedans. Le cahier annonçait « 2 feuilles » de données. | proposée |
| 20 | Chambres vs type | `terrain_avec_pieces` et `chambre_avec_plusieurs_chambres` en avertissement | Hypothèses pédagogiques, seuils dans `settings.py`. | proposée |
| 21 | Statut « corrigé » | Une chaîne numérique propre (`"60581000"`) est `ok`, pas `corrige` | Sinon l'indicateur « enregistrements corrigés » serait gonflé par la simple lecture CSV. | appliquée |
| 22 | Dates relatives (« hier ») | Résolues seulement par rapport à une date connue : `date_mise_a_jour` vs `date_collecte`. Pour `date_collecte`, une date relative reste ambiguë, donc quarantaine | Aucune date de référence fiable pour la collecte. Aucun cas dans les sources. | proposée |
| 23 | Inférence ≠ correction | `type_transaction` déduit (agence) ou fixé par la source (notaires, historique) va dans `inferences`, pas dans `corrections` | Mesuré : sans cette séparation, « corrigés » passait à 2 296 sur 3 184, dont 1 576 uniquement pour ce motif. | appliquée |
| 24 | Règles `chambre_avec_plusieurs_chambres` et `sdb_superieures_chambres_plus_marge` | Gardées en avertissement, **à réévaluer** | Sur les données réelles elles signalent 129 et 121 enregistrements (≈ 4 % chacune) : le nombre de chambres semble tiré au hasard. Utiles pour montrer l'atypie, pas pour juger un bien. | à arbitrer |
