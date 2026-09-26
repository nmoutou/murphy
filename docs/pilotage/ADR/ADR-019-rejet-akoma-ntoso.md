# ADR-019 — Rejet d'Akoma Ntoso comme format de travail

**Statut** : rétro-documenté (décision implicite antérieure au chantier 4)

## Contexte

Akoma Ntoso est le standard XML dominant pour les documents
législatifs/judiciaires. Fallait-il l'adopter comme format pivot ?

## Décision

**Rejet comme format de travail** : trop verbeux, trop permissif, mal
adapté aux pipelines de retrieval. Ses **distinctions ontologiques**
(FRBR Work/Expression/Manifestation, relations de citation typées) sont
**conservées conceptuellement** et informent le modèle Neo4j.

## Alternatives rejetées

- **Adoption pleine** : coût de conversion et de validation
  disproportionné, sans gain pour la récupération.

## Conséquences

- Modèle de données propre (« tronc commun + delta par base » à
  l'étude), aligné sur les DTD DILA réelles.
- Les distinctions FRBR restent la référence conceptuelle du graphe.

## Références

ADR-020
