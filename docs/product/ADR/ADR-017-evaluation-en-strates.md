# ADR-017 — Évaluation en strates de pérennité (T2)

**Statut** : rétro-documenté (décision implicite antérieure au chantier 4)

## Contexte

Les annotations synthétiques de la v0 seront dévaluées par les qrels
expertes de l'alpha. Comment éviter de construire une évaluation
jetable ?

## Décision

Évaluation pensée en **quatre strates de pérennité** :

| Strate | Nature | Annotation | Pérennité |
|---|---|---|---|
| 1 | Invariants structurels (identité canonique, complétude, déterminisme, intégrité des liens) | Aucune | Totale |
| 2 | Qrels citation-minées (garde-fou circularité) | Aucune | Permanente |
| 3 | Métriques appariées relatives (RBO / Jaccard@k, stabilité sous paraphrase) | Aucune | Par construction |
| 4 | Qrels humaines : synthétiques solo (v0) → expertes poolées (alpha) | Forte | Partielle |

**Un seul golden-set** + harnais d'ablations + mini-sets diagnostiques.
Le synthétique v0 est **relégué** (`origin: synthetic`), pas jeté.

## Alternatives rejetées

- **Tout miser sur les qrels humaines** : infrastructure dévaluée à
  chaque changement d'annotateurs.

## Conséquences

- La baseline v0 s'appuie sur les strates 1–3 + citations minées + un
  petit set synthétique ; seule la dernière tranche est dévaluée par
  l'alpha.

## Références

`PROGRAM.md` §5 · ADR-007 · ADR-008
