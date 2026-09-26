# ADR-013 — Alpha en deux phases (option C)

**Statut** : rétro-documenté (décision implicite antérieure au chantier 4)

## Contexte

L'alpha doit à la fois recueillir le besoin des experts et produire le
golden-set canonique. Une phase unique confond les deux objectifs.

## Décision

Alpha en **deux phases** :

- **Ph.1 — Usage & requêtes réelles** : usage réel + annotation inline
  → pool de requêtes réelles.
- **Ph.2 — Qrels canoniques** : campagnes poolées sur ces requêtes →
  golden-set canonique.

## Alternatives rejetées

- **Alpha monophase** : usage seul (pas de qrels canoniques), ou
  campagne d'emblée sans requêtes réelles (qrels hors-sol).

## Conséquences

- L'outil d'annotation devient un **livrable produit** de P3.
- Deux orchestrations d'un même composant de jugement (ADR-010).

## Références

`VERSIONS.md` (alpha ph.1/ph.2) · ADR-010
