# PILOTAGE_log — Journal des revues bimensuelles

> 10 lignes max par entrée, la plus récente en tête (`PILOTAGE.md` §1.4).

## 2026-09-26 — TR-02

- **Fait** : l'adresse du WebSocket est déduite de `NEXT_PUBLIC_API_URL`
  (`frontend/src/lib/chatSocketUrl.ts`) ; `NEXT_PUBLIC_WS_URL` retirée. TR-02 ✅.
- **Vérifié** : `npm run check` vert ; valeur inlinée dans le bundle de dev ; WebSocket
  sur l'adresse déduite : parts `data-parentDocument` et `data-document` reçues ;
  dans le navigateur, les sources s'affichent (pas de réponse : variables LLM vides).
- **Bloqué** : rien. La CI unique passe depuis le push de `main`.
- **Prochain pas** : FE-02 (eslint), puis le code mort du frontend.

## 2026-09-25 — Un seul dépôt (ADR-040), TR-04

- **Fait** : sous-modules réintégrés avec leur historique (4 commits) ; npm workspaces,
  un seul lockfile ; `packages/contract` (schémas zod) remplace les deux `messages.ts` ;
  FE-01 ; Docker depuis la racine ; une CI unique. TR-01, TR-04 et TR-07 ✅.
- **Décidé** : [ADR-040](../product/ADR/ADR-040-depot-unique.md), `packages/` réservé à ce
  qui franchit une frontière d'exécution entre workspaces.
- **Vérifié** : `npm run check` vert (104 tests, `tsc` frontend vert) ; stack de dev et
  images de prod ; aucun `.env` dans les images.
- **Bloqué** : rien.
- **Prochain pas** : pousser, archiver les trois anciens dépôts ; relire et commiter.

## 2026-08-08 — B-08, carte de wayfinding [#1](https://github.com/left-eyebr0w/murphy/issues/1)

- **Fait** : rien de livrable — la carte (*golden-set v1, spécification prête à
  l'authoring*) est en cours : **23 décisions closes, aucun ticket ouvert**, clôture
  **non prononcée**.
- **Décidé** (structurant) : axe unique des mécanismes (liste **7**, composition v1 **5**) ;
  `N_cas` = 150 dont 30 jugés, plancher **30 cas/mécanisme** ; métrique **`RBP(p) + résidu`**,
  `nDCG@R` et `F1@K` **retirés** ([#14](https://github.com/left-eyebr0w/murphy/issues/14)) ;
  **trois hashes** à la place du gel ([#18](https://github.com/left-eyebr0w/murphy/issues/18)) ;
  protocole d'assessment ([#19](https://github.com/left-eyebr0w/murphy/issues/19)) ; plancher de
  composition portant sur le **nom** ([#24](https://github.com/left-eyebr0w/murphy/issues/24)) ;
  **intake des contestations** ([#21](https://github.com/left-eyebr0w/murphy/issues/21)).
- **Vérifié** : aucune question écrite, aucun code touché — la carte est de la planification,
  contrainte posée dans ses propres *Notes*.
- **Bloqué** : rien.
- **Prochain pas** : relire les quatre patches de *Not yet specified*, puis clore la carte ;
  écriture due de **ADR-036** (contenu), **ADR-038** (protocole) et **ADR-032 réécrit**
  (intake + attribution champ → hash).
- **Hygiène** : passe de propagation du 8 août (7 commentaires d'amendement, 7 lignes de carte,
  8 documents). ⚠️ **Ce journal était décroché depuis le 19 juillet** — cette entrée couvre la
  période **d'un bloc**, aucune revue intermédiaire n'est reconstituée.

## 2026-07-19 — B-04

- **Fait** : B-04 (agrégation chunk→document + harnais de scoring) — *intitulé corrigé le 2 août 2026 : il portait « scorer nDCG@R + diagnostics », métrique retirée par [#14](https://github.com/left-eyebr0w/murphy/issues/14) ; le scorer part en B-15*
  passé à ✅. Suite verte (54 tests), mypy strict et ruff propres.
- **Décidé** : **localisation révisée** — nouveau projet dédié `eval/`
  (dossier in-repo, extraction en submodule différée), pas un sous-paquet
  `data/ragcore/evaluation/` comme acté à la Revue #1. Fidèle à ADR-027 (P2
  pilote l'ingestion par sous-processus, sans importer `ragcore`). Diagnostics
  à coupe adaptative (R-Precision, Recall@2R, Doc-Recall@R) maison ; `ranx`
  réduit à MAP + Doc-MRR (sans coupe). Requête R=0 → `None`, exclue des
  moyennes, gardée dans la distribution par requête.
- **Vérifié** : oracle primaire = cas jouets calculés à la main
  (`tests/golden/`, ADR-028) ; cross-check `pytrec_eval` secondaire, hors CI
  par défaut. Constat empirique : `ndcg_cut` de `pytrec_eval` est en gain
  linéaire, pas exponentiel — documenté dans le test, pas supposé à tort.
- **Bloqué** : rien.
- **Prochain pas** : B-05 (adapter baseline) et B-08 (golden-set) tirables en
  parallèle ; B-13 dépend de B-05.
- **Hygiène** : `BACKLOG.md` régularisé (statut B-04, note de localisation).

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
  `ragcore/evaluation/` : agrégation ADR-006 + scorer nDCG@R ADR-007 — *scorer retiré le 2 août 2026, voir B-15*).
- **Hygiène** : documents de cadrage (ADR-025/026/027, STATUS, BACKLOG,
  EXIGENCES_v0, PROGRAM, VERSIONS, VISION, HANDBOOK, INSTITUTIONNEL)
  toujours non commités depuis la session de travail précédente — à
  régulariser.
