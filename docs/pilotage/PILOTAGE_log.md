# PILOTAGE_log — Journal des revues bimensuelles

> 10 lignes max par entrée, la plus récente en tête (`PILOTAGE.md` §1.4).

## 2026-07-19 — B-14

- **Fait** : B-14 (restructuration `conf/` en `base/{workflow,ingestion,evaluation}/`,
  ADR-026) passé à ✅. ADR-026 Proposé → Accepté.
- **Décidé** : sous-dossiers de `base/` (pas de dossiers frères — Kedro
  ne lit que l'env `base/` par défaut) ; re-nesting des blocs mixtes
  `formatting`/`embedding` (Kedro interdit qu'une clé top-level soit
  scindée entre fichiers) ; `evaluation/` en placeholder documenté.
- **Vérifié** : fingerprint identique avant/après
  (`9424808d1c636d533648bbf4e77f2496`), prouvé par
  `golden/test_fingerprint.py` chargeant désormais via le vrai
  `OmegaConfigLoader` (et non plus un `yaml.safe_load` isolé). Suite
  complète (296 tests), mypy strict, ruff : tous verts.
- **Bloqué** : rien.
- **Prochain pas** : B-13 (P2) devient tirable côté prérequis P1 ; B-04
  (scorer) reste l'item P2 retenu à la revue précédente.

## 2026-07-19 — Revue #1

- **Fait** : B-01 (identité canonique croisée), B-02 (`doc_id` LEGI
  stable), B-03 (graphe de citations Neo4j modélisé complètement)
  passés à ✅ — constat du porteur, sans rapport/artefact versionné
  encore référencé pour E-P1-02/03/04.
- **Décidé** : STATUS, BACKLOG, EXIGENCES_v0 mis à jour en conséquence ;
  B-08 devient tirable (B-01 et B-02 acquis). **B-04 retenu** comme
  prochain item. **ADR-028** acté (frontière vérif. auto / assisté /
  humain, règle anti-tautologie) : EXIGENCES_v0 gagne une colonne
  Régime ; le scorer B-04 est *auto pur* (oracle = cas jouets à la
  main, pas de dépendance `pytrec_eval`).
- **Bloqué** : rien.
- **Prochain pas** : implémenter B-04 dans `data/` (sous-paquet
  `ragcore/evaluation/` : agrégation ADR-006 + scorer nDCG@R ADR-007).
- **Hygiène** : documents de cadrage (ADR-025/026/027, STATUS, BACKLOG,
  EXIGENCES_v0, PROGRAM, VERSIONS, VISION, HANDBOOK, INSTITUTIONNEL)
  toujours non commités depuis la session de travail précédente — à
  régulariser.
