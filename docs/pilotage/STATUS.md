# STATUS — État du programme par projet

Dernière mise à jour : 8 août 2026 ([#19](https://github.com/left-eyebr0w/murphy/issues/19)
— précédentes : 5 août [#15](https://github.com/left-eyebr0w/murphy/issues/15), 22 juillet B-07). Structure alignée
sur `PROGRAM.md` §2 (chantier 7). Version en cours : **v0** (voir
`VERSIONS.md`).

> ⚠️ **Où vit l'avancement depuis le 1ᵉʳ août.** La spécification du golden-set
> v1 est conduite comme une **carte de wayfinding** —
> [issue #1](https://github.com/left-eyebr0w/murphy/issues/1) — dont les
> décisions sont indexées dans le corps de l'issue et détaillées dans les
> commentaires de résolution de ses tickets. **Ce tableau n'en est pas le
> miroir** : il suit des livrables, la carte suit des décisions. Un item P2 ne
> passe pas à ✅ parce qu'une décision a été prise.

## P1 — Data

| Sujet | Statut |
|---|---|
| Pipeline LEGI | ✅ Fait, stable |
| Ingestion des 5 bases jurisprudence (CASS, INCA, CAPP, JADE, CONSTIT — ADR-002) | ✅ Fait (vague 1) |
| Régimes d'ingestion dev/prod — trois portes (content/metadata/liens), clés chemin-complet, épuration Mongo (`SCHEMA_VERSION` 2), hydratation Neo4j, interrupteur d'embedding (ADR-022, amendé ADR-023/024) | ✅ Fait (B-00) — prouvé par deux runs réels, bases vérifiées champ par champ |
| Identité canonique vérifiée sur les 3 BDD (ADR-018 — critère de sortie v0) | ✅ Fait (B-01) |
| `doc_id` stable au niveau article pour LEGI (ADR-004) | ✅ Fait (B-02) |
| Graphe de citations Neo4j (source du diagnostic de co-citation, strate 2 — ADR-029) | ✅ Fait (B-03) — modélisation complète : verbes de citation typés, cibles absentes résolues |
| Restructuration `conf/` en partition `workflow / ingestion / evaluation` (ADR-026) | ✅ Fait (B-14) — fingerprint identique avant/après, prouvé via le vrai loader Kedro |

## P2 — Évaluation

| Sujet | Statut |
|---|---|
| Cadrage (`CADRAGE_evaluation` + ADR-004 à 009) | ✅ Fait |
| Agrégation chunk→document + harnais de scoring (ADR-006) | ✅ Fait (B-04) — nouveau projet `eval/`, oracle *auto pur* (cas jouets à la main, ADR-028), cross-check `pytrec_eval` secondaire. ⚠️ **Le scorer `nDCG@R` livré est retiré** le 2 août 2026 ([#14](https://github.com/left-eyebr0w/murphy/issues/14)) ; il part en **B-15** sous la forme `RBP(p) + résidu`. L'agrégation, l'oracle et le gain injectable tiennent |
| Adapter baseline (runs au format ADR-008) | ✅ Fait (B-05) — `BaselineRetriever` Qdrant dense dans `eval/`, `doc_id` lu du payload `identifier` (ADR-018), runs JSONL immuables ; unit + integration testcontainers Qdrant |
| Invariants structurels strate 1 (ADR-017) | ✅ Fait (B-06) — part *pure* dans `eval/` (`core/services/invariants.py`), aucune BDD : rangs contigus/uniques, pas de doublon, ids non vides, namespaces run↔qrels ; loaders JSONL validants (`InvariantError`). Strate 1 *live* (complétude/liens) hors v0, déjà acquise côté data |
| Test statistique apparié (ADR-007) | ❌ À implémenter (B-10) |
| Diagnostic de co-citation (strate 2 — **ADR-029**, ex-« qrels citation-minées ») | ✅ Socle fait (B-07) — commande `murphy-eval-cocitation` dans `eval/`, chemin de lecture Neo4j dédié (hors `ragcore`, ADR-027), artefacts versionnés `eval/artifacts/cocitation/`. **Premier jeu réel : 1456 paires, 726 documents**, reproductible bit-à-bit. Exhaustivité des labels documentaires **prouvée** (1456 avec/sans filtre). ⚠️ Sort du verbe `contains` (726 paires, structure documentaire et non citation) **à trancher avant B-09** |
| Golden-set v1 synthétique + guide d'annotation (ADR-005) | ❌ À produire — **spécification en cours**, conduite en carte de wayfinding ([#1](https://github.com/left-eyebr0w/murphy/issues/1)). Au **8 août** : **22 décisions closes, 1 ticket ouvert** ([#21](https://github.com/left-eyebr0w/murphy/issues/21) — *comment une correction entre dans la collection*), non bloqué, non réclamé ; c'est le **dernier ticket de la carte**. Acquis structurants — axe unique des mécanismes (**liste 7, composition v1 5**), `N_cas` = 150 dont 30 jugés et `N_q` ≥ 180, plancher de **30 cas/mécanisme**, métrique **`RBP(p) + résidu`** (`nDCG@R` et `F1@K` retirés) avec un **`p` de décision `0,80` venu du lecteur** et une **famille sentinelle** sans seuil ([#19](https://github.com/left-eyebr0w/murphy/issues/19), ADR-007 §4 réécrit — *la règle `p = 0,01^(1/d̄)` est retirée*), trois hashes d'identification à la place du gel, protocole de pooling à **allocation gloutonne pour l'admission** et **règle de famine pour la redondance**, **huit** contraintes de rédaction acquises pour le guide, et un **plancher de composition qui porte sur le *nom*** ([#24](https://github.com/left-eyebr0w/murphy/issues/24)) — deux conditions, *contenu* (≥ 1 composant jugé) et *monotonie* (composition livrée ⊆ composition déclarée), lues **une fois avant déclaration** et **pré-enregistrées** ; sous le plancher l'objet se déclare et se publie, mais **sous un autre nom**, en portant écrit que **son résidu nul n'est pas un signal de qualité**. **Rien n'est écrit tant que la carte n'est pas close** : elle s'arrête avant la première question et avant tout code, et atterrit en **ADR-036** (contenu) et **ADR-038** (protocole d'assessment) |

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
