# ADR-014 — Exhaustivité DILA = critère de publication

**Statut** : rétro-documenté (décision implicite antérieure au chantier 4)

## Contexte

L'exhaustivité du corpus est un invariant de vision (`VISION.md`), mais
l'exiger dès les premières versions bloquerait tout.

## Décision

L'exhaustivité DILA est un critère de **publication** — pas de v0 ni de
beta. Ingestion **progressive**, priorisée par valeur pour les experts
(cf. ADR-003).

## Alternatives rejetées

- **Exhaustivité préalable** : irréaliste, contraire au principe de
  capacités mesurables.
- **Renoncement à l'exhaustivité** : contraire à l'invariant de vision.

## Conséquences

- L'exigence devient un critère de sortie daté par capacité, pas un
  préalable paralysant.

## Références

`VISION.md` §2 · ADR-003 · `VERSIONS.md` (publication)
