# ADR-004 — Définition de l'unité « document »

**Statut** : acté (chantier 4, 17 juillet 2026)

## Contexte

L'évaluation à deux niveaux (passage + document) exige une définition
stable de l'unité « document » (`CADRAGE_evaluation` §2, §9). Candidats :
arrêt entier, article, section, fichier XML.

## Décision

Définition **fonctionnelle, non géométrique** : l'unité de **citation
juridique canonique de chaque base** — la **décision** (ECLI) en
jurisprudence, l'**article** pour LEGI. Règle d'extension aux vagues
suivantes : *ce qu'un juriste cite*.

## Alternatives rejetées

- **Définitions géométriques** (fichier, section) : dépendent de
  l'archivage DILA, instables entre bases.
- **Unité unique inter-bases** : la pratique de citation diffère par
  nature entre corpus.

## Conséquences

- Métriques document rapportées **par base** en plus de l'agrégé.
- L'identité canonique doit exposer un **`doc_id` stable à ce niveau** —
  point ouvert : à vérifier côté pipeline LEGI pour l'article.

## Références

ADR-006 (agrégation) · ADR-007 (métriques) · ADR-018 (identité)
