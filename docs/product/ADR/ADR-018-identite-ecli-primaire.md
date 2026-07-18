# ADR-018 — Identité : ECLI primaire

**Statut** : rétro-documenté (décision implicite antérieure au chantier 4)

## Contexte

Tout document et tout fragment doit porter un identifiant stable et
unique, partagé par les trois bases (invariant de vision). Candidats :
ECLI, ELI, IDs internes DILA, numéros métier.

## Décision

- **ECLI** = identifiant stable **primaire** en jurisprudence.
- **IDs internes DILA** (JURITEXT…) = clés techniques de partition.
- **Numéros métier** (pourvoi, requête…) = fallback.
- **ELI non retenu strictement.**

**Invariant bloquant** : un même chunk/document porte le **même ID**
dans Qdrant, Neo4j et MongoDB.

## Alternatives rejetées

- **ELI strict** : couverture et stabilité insuffisantes sur le
  périmètre jurisprudentiel.
- **IDs DILA comme primaire** : internes, non citables, non pérennes.

## Conséquences

- Sans cette couche d'identité, ni l'évaluation agnostique ni la boucle
  experts ne sont possibles.
- Point ouvert (ADR-004) : `doc_id` stable au niveau article pour LEGI.
- Sous-document : schéma d'identifiant sous l'ECLI non résolu (index
  simple suffisant à ce stade).

## Références

`VISION.md` §2 · ADR-004 · ADR-020
