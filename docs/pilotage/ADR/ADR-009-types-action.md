# ADR-009 — Types d'action (stratification v0)

**Statut** : acté (chantier 4, 17 juillet 2026) — liste révisable en alpha ph.1
— **amendé par ADR-030** (22 juillet 2026) : l'axe difficulté est supprimé, le
type passe de la requête à l'arête `(requête, source, cible)` et cesse d'être
exclusif, `jurisprudence_sur_question` devient `jurisprudence_applicable`. Les
quatre types ci-dessous subsistent au sein d'une liste plate de huit
opérations. **L'exclusion de la vigueur temporelle reste entière** : elle vise
la capacité produit, non le typage d'une arête en évaluation (ADR-030 §
`succession_temporelle`).

## Contexte

La stratification des requêtes par type d'action
(`CADRAGE_evaluation` §3.2, §9) devait être fixée pour la v0.

## Décision

**Quatre types = quatre capacités mesurées séparément** :
`texte_applicable` · `jurisprudence_sur_question` · `known_item` ·
`graph_hop` (intègre le set diagnostique exigé par la DoD).

- **Exclus de la v0** : vigueur temporelle, multi-tours.
- Axe difficulté orthogonal inchangé.
- Liste **révisable en alpha ph.1 sans migration**.

## Alternatives rejetées

- **Typologie plus fine d'emblée** : spéculative avant les requêtes
  réelles de l'alpha.

## Conséquences

- Les rapports d'évaluation ventilent par type.
- `graph_hop` mesure directement la valeur de l'augmentation Neo4j.

## Références

ADR-017 (strates) · `VERSIONS.md` (DoD v0)
