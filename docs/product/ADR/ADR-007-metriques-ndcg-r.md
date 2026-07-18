# ADR-007 — Métriques sans coupes constantes (nDCG@R)

**Statut** : acté (chantier 4, 17 juillet 2026)

## Contexte

`CADRAGE_evaluation` §9 demandait de fixer des valeurs de k. Or les k
fixes relèvent du modèle web search (affichage top-k), incompatible avec
l'invariant d'exhaustivité des sources.

## Décision

**Rejet des k fixes.**

- Métrique de décision **unique** : **nDCG@R** (coupe adaptative = nombre
  de pertinents de la requête), **test statistique apparié** dessus.
- Diagnostics : MAP, R-Precision, Recall@2R (passage) ; Doc-MRR,
  Doc-Recall@R (document).
- Côté produit : listes de longueur variable par **seuil de score** — le
  seuil est une stratégie de config.
- Seule profondeur opérationnelle restante : le **pooling** (paramètre de
  collecte, définissable en multiple de R).

## Alternatives rejetées

- **nDCG@k / Recall@k à k constants** : cohérents avec un affichage
  top-k que Murphy n'a pas.

## Conséquences

- Sensibilité accrue à la **complétude des qrels** (R dépend des
  jugements) → importance renforcée du pooling et des citations minées.

## Références

ADR-006 (agrégation) · ADR-017 (strates) · `VERSIONS.md` (DoD v0)
