# ADR-006 — Agrégation chunk→document

**Statut** : acté (chantier 4, 17 juillet 2026)

## Contexte

Un seul jeu de qrels au niveau chunk doit produire les métriques passage
**et** document (`CADRAGE_evaluation` §4).

## Décision

- Côté **qrels** : **max** — le document vaut son meilleur chunk (pas de
  biais de taille).
- Côté **runs** : **rang du premier chunk** du document.
- Les fusions de scores sophistiquées sont des **stratégies de config
  évaluées**, jamais des règles du harnais.

## Alternatives rejetées

- **`sum` plafonné ou moyennes** : introduisent un biais de taille de
  document.
- **Fusion dans le harnais** : contaminerait la mesure par un choix de
  pipeline.

## Conséquences

- Le scorer reste trivial et neutre ; toute intelligence d'agrégation se
  mesure comme n'importe quelle config.

## Références

ADR-004 (unité document) · ADR-007 (métriques)
