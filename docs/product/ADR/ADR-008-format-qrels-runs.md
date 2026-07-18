# ADR-008 — Format de stockage qrels/runs

**Statut** : acté (chantier 4, 17 juillet 2026)

## Contexte

Le format doit servir le harnais v0 et l'outil d'annotation expert
(alpha), et conserver la provenance des jugements.

## Décision

Stockage canonique **JSONL versionné**, un jugement par ligne :
`query_id`, `doc_id`, `chunk_id`, `q1/q2/q3`, `grade` (dérivé —
redondance assumée), `origin`, `annotator`, `timestamp`,
`guide_version`. Les réponses q1–q3 permettent de localiser les
désaccords et de re-dériver les grades. **Projections déterministes**
vers qrels/runs TREC plats pour l'outillage standard (trec_eval,
pytrec_eval, ranx).

## Alternatives rejetées

- **TREC plat comme format canonique** : perd q1–q3, la provenance et le
  versionnement du guide.

## Conséquences

- L'outillage IR standard reste utilisable sans adaptation.
- Le JSONL canonique reste la seule source de vérité.

## Références

ADR-005 (cascade q1–q3) · ADR-010 (composant de jugement)
