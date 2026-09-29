# ADR-002 — Périmètre jurisprudentiel de la v0

**Statut** : acté — décision **constatée** (17 juillet 2026)

## Contexte

Restait ouvert : ingérer les 5 bases de jurisprudence DILA, ou un
sous-ensemble couvrant les deux ordres (p. ex. CASS + JADE), suffisant
pour prouver la réplicabilité de la méthode.

## Décision

**Les 5 bases** : CASS, INCA, CAPP, JADE, CONSTIT. Décision constatée —
le travail était déjà implémenté. Justification a posteriori :
réplicabilité prouvée sur toute la variété structurelle DILA (dont le
cas piégeux CASS/INCA à racine XML commune) et socle judiciaire complet
pour l'alpha.

## Alternatives rejetées

- **Sous-ensemble CASS + JADE** : suffisant pour la réplicabilité, mais
  socle incomplet pour les experts ; l'économie était caduque, le
  travail étant fait.

## Conséquences

- Pour chacune des 5 bases, l'identité canonique est vérifiée sur les
  3 bases de données.

## Références

ADR-003 (séquençage) · ADR-004 (unité document)
