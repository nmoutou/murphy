# ADR-003 — Séquençage d'ingestion DILA

**Statut** : acté (17 juillet 2026) — clôture vague 2 différée

## Contexte

L'exhaustivité DILA est un critère de publication (ADR-014) ; il fallait
ordonner l'ingestion, priorisée par valeur pour les experts.

## Décision

- **Vague 1** (v0) : les 5 bases de jurisprudence (CASS, INCA, CAPP,
  JADE, CONSTIT) — *fait*.
- **Vague 2** (→ beta) : **JORF** + base(s) **à déterminer sur les
  retours alpha** (candidates : KALI, CIRCULAIRES).
- **Vague 3** (→ publication) : solde DILA (DOLE, CNIL, débats/QR
  parlementaires, SARDE, protocoles…).

Le choix différé du contenu de la vague 2 est assumé, cohérent avec le
principe de versions par capacités mesurables (ADR-012).

## Alternatives rejetées

- **Séquence figée dès maintenant** (JORF + KALI, proposition
  initiale) : fige un arbitrage que l'alpha informera mieux.

## Conséquences

- Un **mini-ADR de clôture** du choix de la vague 2 sera rédigé à
  l'issue de l'alpha.

## Références

ADR-012 · ADR-014
