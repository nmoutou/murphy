# STATUS — État du programme par projet

Dernière mise à jour : 19 juillet 2026 (B-04). Structure alignée
sur `PROGRAM.md` §2 (chantier 7). Version en cours : **v0** (voir
`VERSIONS.md`).

## P1 — Data

| Sujet | Statut |
|---|---|
| Pipeline LEGI | ✅ Fait, stable |
| Ingestion des 5 bases jurisprudence (CASS, INCA, CAPP, JADE, CONSTIT — ADR-002) | ✅ Fait (vague 1) |
| Régimes d'ingestion dev/prod — trois portes (content/metadata/liens), clés chemin-complet, épuration Mongo (`SCHEMA_VERSION` 2), hydratation Neo4j, interrupteur d'embedding (ADR-022, amendé ADR-023/024) | ✅ Fait (B-00) — prouvé par deux runs réels, bases vérifiées champ par champ |
| Identité canonique vérifiée sur les 3 BDD (ADR-018 — critère de sortie v0) | ✅ Fait (B-01) |
| `doc_id` stable au niveau article pour LEGI (ADR-004) | ✅ Fait (B-02) |
| Graphe de citations Neo4j (source qrels citation-minées) | ✅ Fait (B-03) — modélisation complète : verbes de citation typés, cibles absentes résolues |
| Restructuration `conf/` en partition `workflow / ingestion / evaluation` (ADR-026) | ✅ Fait (B-14) — fingerprint identique avant/après, prouvé via le vrai loader Kedro |

## P2 — Évaluation

| Sujet | Statut |
|---|---|
| Cadrage (`CADRAGE_evaluation` + ADR-004 à 009) | ✅ Fait |
| Scorer nDCG@R + diagnostics + agrégation chunk→document (ADR-006/007) | ✅ Fait (B-04) — nouveau projet `eval/`, oracle *auto pur* (cas jouets à la main, ADR-028), cross-check `pytrec_eval` secondaire |
| Adapter baseline (runs au format ADR-008) | ❌ À implémenter (B-05) |
| Test statistique apparié (ADR-007) | ❌ À implémenter (B-10) |
| Qrels citation-minées (strate 2) | ❌ À implémenter |
| Golden-set v1 synthétique + guide d'annotation (ADR-005) | ❌ À produire |

## P3 — Applicatif

| Sujet | Statut |
|---|---|
| Pipeline RAG MVP (embedding → retrieval → fetch → LLM streamé + sources) | ✅ Opérationnel — **en pause** (réveil prévu : alpha ph.1) |
| Transports (WebSocket, SSE, completions JSON) + frontend chat | ✅ Opérationnel |
| Health check + observabilité (logs Pino, `ragTiming`) | ✅ Opérationnel |
| Neo4j (enrichissement graphe) | 🟡 Provisionné, non câblé |
| Composant de jugement + mode annotation inline (ADR-010) | ❌ Alpha ph.1 |
| Mode campagne poolée (ADR-010) | ❌ Alpha ph.2 |
| Environnements public/panel (télémétrie opt-in, interleaving — ADR-025), OAuth 2.0, métriques sans contenu | ❌ Beta |

Limites assumées du MVP : stateless (pas d'historique serveur),
fail-fast (pas de retry/fallback LLM), pas d'authentification, GPU
requis pour l'embedding TEI (ADR-020).

## Cadrage

| Chantier | Statut |
|---|---|
| 1 Vision · 2 Programme · 3 Versions · 4 Décisions · 5 Registre ADR · 6 Pilotage · 7 Nettoyage | ✅ Faits |
| 8 Institutionnel | 🟡 Squelette validé ; ADR-INST-01/02/03 et livrables 2–4 ouverts |
