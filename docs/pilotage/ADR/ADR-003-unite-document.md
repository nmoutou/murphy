# ADR-003 — Définition de l'unité « document »

**Statut** : acté (17 juillet 2026)

## Contexte

L'identité canonique et le contrat entre ingestion et serving (ADR-015)
reposent sur une définition stable de l'unité « document ». Candidats :
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

- L'identité canonique doit exposer un **`doc_id` stable à ce niveau** —
  point ouvert : à vérifier côté pipeline LEGI pour l'article.

## Références

ADR-008 (identité) · ADR-015 (contrat ingestion / serving)
