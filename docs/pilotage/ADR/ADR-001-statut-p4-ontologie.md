# ADR-001 — Statut du volet Ontologie (P4)

**Statut** : acté (chantier 4, 17 juillet 2026) — **P4 abandonné, plus à
l'horizon (18 juillet 2026)**

## Contexte

Trois projets opérationnels (P1 Data, P2 Évaluation, P3 Applicatif) + un
volet doctoral (P4 Ontologie). Fallait-il l'intégrer au programme
opérationnel ou le maintenir à l'extérieur ?

## Décision

P4 est **hors programme opérationnel, interfaces déclarées**. La relation
P4→P1 est documentée comme **influence** (distinctions FRBR
Work/Expression/Manifestation, citations typées informant le modèle
Neo4j), non comme dépendance : **aucun jalon du programme n'attend un
livrable doctoral**.

## Alternatives rejetées

- **Intégration de P4 au programme** : couplerait les versions
  opérationnelles au rythme et aux critères doctoraux.

## Conséquences

- Le programme avance indépendamment ; P4 consomme les artefacts de P1
  sans les bloquer.
- **Point ouvert** : formaliser ou non un contrat de stabilité inverse
  P1→P4 (engagement de non-régression sur le graphe de citations typées).

## Références

`PROGRAM.md` §2 · ADR-019 (distinctions ontologiques conservées)
