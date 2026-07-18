# ADR-005 — Échelle de pertinence et guide d'annotation

**Statut** : acté (chantier 4, 17 juillet 2026)

## Contexte

La pertinence graduée est un invariant (ADR-016). Restait à figer
l'échelle, utilisable en solo (v0) comme par les experts (alpha).

## Décision

Grades **0–3 dérivés d'une cascade de trois tests binaires** :

| Test | Question | Si non |
|---|---|---|
| Q1 | Même question de droit ? | grade 0 |
| Q2 | Citable dans une consultation ? | grade 1 |
| Q3 | Support principal de la solution ? | grade 2 (oui → 3) |

Conventions :

- Pertinence **topique, non directionnelle** : un arrêt contraire bien
  en point est un 3.
- Citations minées à **grade 2 par défaut, surclassables**.
- **Guide d'annotation** = documentation des trois questions avec cas
  limites, écrit **dès la v0** pour servir tel quel en alpha ph.2.

## Alternatives rejetées

- **Échelle à démarcations d'intensité** (« directement applicable /
  support / périphérique / hors-sujet ») : arbitraire, désaccords non
  localisables.

## Conséquences

- q1–q3 stockées avec le grade (ADR-008) : désaccords localisables à la
  question près, grades re-dérivables.
- Le composant de jugement (ADR-010) implémente la cascade, pas une
  saisie directe du grade.

## Références

ADR-008 (format) · ADR-010 (composant de jugement) · ADR-016
