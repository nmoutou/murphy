# ADR-007 — Métriques sans coupes constantes (nDCG@R)

**Statut** : acté (chantier 4, 17 juillet 2026)

## Contexte

`CADRAGE_evaluation` §9 demandait de fixer des valeurs de k. Or les k
fixes relèvent du modèle web search (affichage top-k), incompatible avec
l'invariant d'exhaustivité des sources.

## Décision

**Rejet des k fixes.**

- Métrique de décision **unique** : **nDCG@R** (coupe adaptative = nombre
  de pertinents de la requête), **test statistique apparié** dessus.
- Diagnostics : MAP, R-Precision, Recall@2R (passage) ; Doc-MRR,
  Doc-Recall@R (document).
- Côté produit : listes de longueur variable par **seuil de score** — le
  seuil est une stratégie de config.
- Seule profondeur opérationnelle restante : le **pooling** (paramètre de
  collecte, définissable en multiple de R).

## Alternatives rejetées

- **nDCG@k / Recall@k à k constants** : cohérents avec un affichage
  top-k que Murphy n'a pas.

## Conséquences

- Sensibilité accrue à la **complétude des qrels** (R dépend des
  jugements) → importance renforcée du **pooling**. *(Amendé par
  ADR-029 : les citations minées, initialement citées ici comme second
  levier, ne sont plus une source de qrels — la strate 2 est un
  diagnostic de précision. La complétude des qrels repose donc
  entièrement sur le pooling et sur le golden-set humain, B-08.)*

- **Corollaire pour toute ventilation** (par opération, par base) : restreindre
  les qrels à un sous-ensemble **change R, donc la coupe**. Une ventilation est
  une **mesure distincte**, à dénominateur propre — elle ne se compare ni à
  l'agrégat ni à une autre ventilation (ADR-030).

## Références

ADR-006 (agrégation) · ADR-017 (strates) · ADR-029 (strate 2
rétrogradée) · ADR-030 (ventilation par opération) · `VERSIONS.md` (DoD v0)
