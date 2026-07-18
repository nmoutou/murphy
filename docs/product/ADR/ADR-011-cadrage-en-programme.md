# ADR-011 — Cadrage en programme

**Statut** : rétro-documenté (décision implicite antérieure au chantier 4)

## Contexte

L'écosystème Murphy couvre data, évaluation et applicatif. Le
structurer comme un projet unique ou comme un programme ?

## Décision

L'écosystème complet est structuré en **programme à trois projets**
(P1 Data, P2 Évaluation, P3 Applicatif), avec **interfaces
contractualisées** (`PROGRAM.md` §2.2) : IDs canoniques, payloads,
contrat d'adapter.

## Alternatives rejetées

- **Projet unique** : frontières floues, évaluation non agnostique,
  couplage des rythmes.

## Conséquences

- Les frontières passent par des contrats — condition de l'évaluation
  agnostique et de la boucle experts.

## Références

`PROGRAM.md` §2
