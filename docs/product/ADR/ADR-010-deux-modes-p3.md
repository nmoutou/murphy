# ADR-010 — Architecture des deux modes d'annotation de P3

**Statut** : acté (chantier 4, 17 juillet 2026)

## Contexte

P3 porte deux usages d'annotation : inline (alpha ph.1, au fil de l'eau
sur requêtes réelles) et campagne poolée (ph.2). Risque de divergence
des formats de jugement.

## Décision

Un **composant de jugement unique** (rendu du passage + cascade q1→q3 +
écriture JSONL canonique), **deux orchestrations** :

- **Inline** (ph.1) : collecte opportuniste sur requêtes réelles,
  `origin: inline`.
- **Campagne** (ph.2) : file poolée, guide d'annotation affiché,
  calibration inter-experts, progression trackée.

## Alternatives rejetées

- **Deux composants séparés** : deux formats qui divergent, jugements
  non comparables.

## Conséquences

- Risque documenté : si la cascade s'avère trop lourde en inline,
  **réviser la cascade elle-même** (ADR-005) — jamais créer deux formats
  de jugement divergents.

## Références

ADR-005 · ADR-008 · ADR-013 (alpha en deux phases)
