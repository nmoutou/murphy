# ADR-017 — Évaluation en strates de pérennité (T2)

**Statut** : rétro-documenté (décision implicite antérieure au chantier 4)
— **amendé par ADR-025** (ajout de la strate « signaux online panel »)
— **amendé par ADR-029** (strate 2 rétrogradée : diagnostic de
co-citation, non qrels)

## Contexte

Les annotations synthétiques de la v0 seront dévaluées par les qrels
expertes de l'alpha. Comment éviter de construire une évaluation
jetable ?

## Décision

Évaluation pensée en **strates de pérennité** — quatre offline à
l'origine, plus une strate online panel ajoutée par ADR-025 :

| Strate | Nature | Annotation | Pérennité |
|---|---|---|---|
| 1 | Invariants structurels (identité canonique, complétude, déterminisme, intégrité des liens) | Aucune | Totale |
| 2 | Diagnostic de co-citation, précision-seulement (garde-fou circularité — **ADR-029**, ex-« qrels citation-minées ») | Aucune | Permanente |
| 3 | Métriques appariées relatives (RBO / Jaccard@k, stabilité sous paraphrase) | Aucune | Par construction |
| 4 | Qrels humaines : synthétiques solo (v0) → expertes poolées (alpha) | Forte | Partielle |
| 5 | Signaux online panel (CTR, dwell time, abandon, reformulation, interleaving — beta, ADR-025) | Aucune (télémétrie consentie, opt-in) | Liée au panel ; **comparaisons relatives uniquement** |

**Un seul golden-set** + harnais d'ablations + mini-sets diagnostiques.
Le synthétique v0 est **relégué** (`origin: synthetic`), pas jeté.

## Alternatives rejetées

- **Tout miser sur les qrels humaines** : infrastructure dévaluée à
  chaque changement d'annotateurs.

## Conséquences

- La baseline v0 s'appuie sur les strates 1–3 + le **diagnostic de
  co-citation** (strate 2, précision-seulement — ADR-029, non une source
  de qrels) + un petit set synthétique ; seule la dernière tranche est
  dévaluée par l'alpha.
- À partir de la beta, les signaux comportementaux de l'environnement
  panel (strate 5 — ADR-025) deviennent une source supplémentaire de
  diagnostics/qrels ; ils ne servent qu'à départager des configs
  (verdicts relatifs), jamais à mesurer une qualité absolue. Les
  strates 1–4 restent le socle offline.

## Références

`PROGRAM.md` §5 · ADR-007 · ADR-008 · ADR-025 (strate 5) · ADR-029
(strate 2 rétrogradée)
