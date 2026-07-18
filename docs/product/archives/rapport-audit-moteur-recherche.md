# Rapport d'audit — Programme « Moteur de recherche »

| | |
|---|---|
| **Cadrage de référence** | `cadrage-audit-moteur-recherche.md` v0.2 (2026-07-17) |
| **Type de document** | Rapport d'audit (constats + registre + delta v0 + écarts ADR) |
| **Date de l'audit** | 2026-07-18 |
| **Auditeur** | Nicolas Moutou (audit outillé, agent Claude Code) |
| **Statut** | Constats établis — à valider |

## Instantané de référence (borne temporelle, §3 du cadrage)

| Dépôt | Commit | État du working tree |
|---|---|---|
| parent `murphy/` | `492e54b` | modifié (réorganisation `docs/`, `.env.example`, compose) |
| `backend/` | `7330f40` (2026-06-27) | **3 fichiers non commités** : `src/infra/collectionPointer.ts` (nouveau), `src/infra/index.ts`, `src/server.ts` |
| `frontend/` | `38955b3` (2026-06-27) | propre |
| `data/` | `0b160f1` « Qualité » (2026-07-16) | propre |

État des bases au moment de l'audit : run publié `b727df00…` (2026-07-16), collection Qdrant `9424808d1c636d533648bbf4e77f2496`. L'audit porte sur les **fichiers tels quels** (modifications non commitées incluses, signalées comme telles).

---

## 1. Synthèse

**Où en est le programme par rapport à la DoD v0 :** un item sur sept est atteint et vérifié (l'identité canonique, l'invariant bloquant) ; les six autres — tous portés par P2 — sont **absents** : aucun code de harnais d'évaluation n'existe dans les dépôts. Le delta v0 est donc net et concentré : **la v0 se joue entièrement sur l'implémentation de P2**, plus deux prérequis data (résolution des relations pendantes, volumétrie cible à trancher).

Constats saillants, preuve à l'appui :

1. **A4 — l'invariant d'identité canonique tient, empiriquement, sur les 3 BDD** : 22/22 identifiants échantillonnés (5 familles, seed 42) portent le même `identifier` sérialisé dans Qdrant, MongoDB **et** Neo4j. Neo4j est bien câblé côté *ingestion* (1 189 nœuds, 1 236 arêtes) — la mention « non câblé » de `STATUS.md` ne vaut que pour le *serving*.
2. **A2 — le harnais est intégralement à construire** : pas d'adapter, pas de qrels, pas de scorer, pas de golden-set, pas de baseline (recherches exhaustives négatives). Conforme au statut annoncé « cadré, non implémenté » — c'est le delta v0.
3. **A1 — le pipeline est en bonne santé (280 tests verts, 82 % de couverture, 0 document perdu sur le dernier run), mais le corpus est un échantillon** : CAPP = 1 document, INCA = 1, CONSTIT = 2. « Les 5 bases ingérées » est vrai au sens de la réplicabilité, pas de la volumétrie. La DoD ne fixe aucune volumétrie cible : c'est une décision à acter.
4. **A3 (hors DoD v0) — le chemin RAG de bout en bout est actuellement rompu**, contrairement à `STATUS.md` : le backend lit `payload.chunkId` là où le pipeline écrit `chunk_id`, et fetch Mongo une collection `chunks` qui n'existe plus. Démontré à l'exécution : recherche Qdrant OK puis `"No documents to fetch (empty chunkId list)"`, zéro source streamée. Une adaptation est en cours (pointeur de collection, non commité) mais ne couvre pas encore le contrat de payload.
5. **A5 — une décision actée diverge du code** (ADR-018 « ECLI primaire » vs clé effective DILA + ECLI en métadonnée remplie à 43 %), et plusieurs décisions structurantes vivent dans le code **sans ADR** (fingerprint→collection + pointeur publié, `owner_id`, normalisation v1 hashée).

---

## 2. Registre des constats

Cotation : **Niveau** (Conforme / Écart mineur / Écart majeur / Non couvert) · **Gravité** (Bloquant / Élevé / Modéré / Faible) · **Périmètre** (v0 / hors-v0) · **Nature** (Fait / Prévu / Supposé).

### Axe A4 — Identité canonique inter-BDD (audité en premier)

**A4-01 — Invariant vérifié sur les 3 BDD.** `Conforme · — · v0 · Fait`
Un même document porte le même identifiant sérialisé (`eli:LEGIARTI…`, `decision:JURITEXT…`) dans les trois bases. Vérification croisée sur 22 identifiants tirés au hasard (seed 42) couvrant les 5 familles (LEGIARTI, LEGITEXT, JURITEXT, CETATEXT, CONSTEXT) : **22/22 présents dans Qdrant (payload `identifier`), MongoDB (`LEGIFRANCE.documents`, clé `identifier`) et Neo4j (propriété `identifier`)**.
*Preuves :* script `audit_a4.py` (échantillonnage consigné en annexe) ; code : `ELI.serialize()` / `DecisionId.serialize()` uniques (`ragcore/core/models/identifiers.py:75-135`), utilisés à l'identique par `mongo/document_repository.py:44`, `qdrant/vector_repository.py:68`, `neo4j/graph_repository.py:71`.

**A4-02 — L'identité *chunk* ne vit que dans Qdrant.** `Écart mineur · Modéré · v0 · Fait`
`chunk_id = {identifier.raw}_{ordinal:04d}` (`sources/generic/chunking.py:135`) — déterministe, dérivé du parent, `doc_id` recouvrable par troncature. Mais il n'est **référencé que dans Qdrant** : Mongo stocke des documents entiers (pas de collection chunks), Neo4j n'a pas de nœuds chunk. `CADRAGE_evaluation` §2 dit « Qdrant, Neo4j et MongoDB référencent tous ce même `chunk_id` / `doc_id` » : satisfait pour `doc_id`, pas pour `chunk_id`. Ne bloque pas l'évaluation (les runs/qrels peuvent s'écrire au niveau chunk depuis Qdrant, l'agrégation document se dérive), mais l'écart avec la lettre du cadrage doit être **assumé par écrit** (amender le §2, ou stocker les chunks ailleurs).
*Preuves :* collections Mongo = `[documents, manifest]` (constaté) ; propriétés de nœuds Neo4j = `{owner_id, identifier, title, schema_version, source, text}` (constaté).

**A4-03 — ID de point Qdrant stable et traçable.** `Conforme · — · v0 · Fait`
ID de point = SHA-256(`chunk_id`) mod 2⁶³ — stable inter-processus (contrairement à `hash()` Python), `chunk_id` conservé en clair dans le payload.
*Preuve :* `qdrant/vector_repository.py:77-86`.

### Axe A1 — P1 Data : ingestion & modèle

**A1-01 — Les 6 sources sont câblées et ingérées, mais sur un corpus d'échantillon.** `Écart mineur · Élevé · v0 · Fait`
Dernier run publié (`b727df00…`, 2026-07-16) : statut `ok`, `fetched 1121 == persisted 1121`, **0 document perdu**. Répartition Mongo : legi 769, jade 256, cass 92, **capp 1, inca 1, constit 2**. Le corpus source (`/mnt/data/Murphy/src`) contient exactement : LEGI 2 564 XML, JADE 256, CASS 92, CONSTIT 2, **CAPP 1, INCA 1**. La réplicabilité sur toute la variété structurelle DILA (dont la racine commune CASS/INCA) est prouvée ; la volumétrie de production ne l'est pas. La DoD v0 ne chiffre aucune volumétrie : **décision à acter** (échantillon suffisant pour v0 « mesurable », ou ingestion complète des 5 bases ?).
*Preuves :* `data/data/08_reporting/stats/2026-07-16T12.54.29.317Z_b727df00….json` ; comptage XML par `find` ; agrégation Mongo par source.

**A1-02 — Cohérence Mongo ↔ Qdrant : aucun document perdu à l'embedding.** `Conforme · — · v0 · Fait`
18 023 chunks Qdrant couvrant 811 documents distincts. Les 310 documents Mongo absents de Qdrant ont **tous un contenu vide** (287 sections `LEGISCTA` + 23 `LEGITEXT` structurels) — aucun document à contenu non vide sans vecteurs. Inversement, 0 document Qdrant absent de Mongo. Dimension 768, distance Cosine, modèle fingerprinté `all-mpnet-base-v2` : aligné avec le TEI servi (`/info` : même `model_id`).
*Preuves :* script `audit_a1.py` ; `GET /collections/9424808d…` ; `GET :5001/info`.

**A1-03 — Remplissage réel mesuré ; deux anomalies de typage/complétude.** `Écart mineur · Modéré · v0 · Fait`
Taux de remplissage mesurés sur les 1 121 documents (table complète en annexe). Deux faits notables : **(a)** `type_document = "Texte"` pour **256/256 décisions JADE** là où le judiciaire porte `ARRET` — une décision du Conseil d'État typée comme un texte ; **(b)** ECLI présent sur **153/352 décisions** seulement (cass 92/92, constit 2/2, jade 59/256, capp 0/1, inca 0/1).
*Preuves :* agrégations Mongo consignées (sorties `audit_a1.py`).

**A1-04 — Unité « document » LEGI au niveau article : vérifié (point ouvert d'ADR-004 levé).** `Conforme · — · v0 · Fait`
Le `doc_id` LEGI est bien l'article (`eli:LEGIARTI…`, 384 documents, 2 869 chunks). Nuance à connaître : les **Textes** (`LEGITEXT`, 98 documents) sont aussi des unités embarquées (434 chunks) — la récupération peut donc retourner des unités « texte » en plus des articles ; les Sections sont stockées mais vides, non embarquées.
*Preuve :* répartition par préfixe d'identifiant (Mongo + Qdrant).

**A1-05 — Santé du pipeline : tests et déterminisme.** `Conforme · — · v0 · Fait`
`pytest` : **280 tests verts, 0 échec, couverture 82 %** (unitaires + intégration + golden-master corpus/vocabulaire/fingerprint). Déterminisme structurel : collection Qdrant dérivée de l'empreinte de la `WorkflowConfig` (jamais nommée à la main), IDs stables, publication du pointeur réservée aux runs `ok`.
*Preuves :* sortie pytest (2026-07-18) ; `core/config/fingerprint.py` ; `hooks.py:607-642` (`_publish_collection`).

**A1-06 — Graphe de citations très incomplet : 19 032 relations pendantes pour 1 236 arêtes écrites.** `Écart majeur · Élevé · v0 · Fait`
Le run 2026-07-16 compte `relation.pending: 19032` contre `relation.upserted: 1274` ; le graphe contient 1 236 arêtes et 68 nœuds `Unknown` (cibles décrites, non identifiées — les `<LIEN>` juri ont tous leurs attributs vides). La passe de résolution (extracteur de références + registre d'alias) n'existe pas encore. **Conséquence v0 directe** : les qrels citation-minées (strate 2) et le set graph-hop de la DoD dépendent d'un graphe exploitable.
*Preuves :* stats du run ; comptages Neo4j ; doctrine `UnknownRef` (`identifiers.py:155-187`).

### Axe A2 — P2 Évaluation : harnais IR (le delta v0)

Recherche exhaustive dans les trois dépôts (`ndcg|qrels|trec|golden.set|pytrec|ranx|ir_measures|graph.hop|scorer|adapter`) : **aucun code, aucun artefact**. Les seuls JSONL du dépôt data sont la télémétrie de runs (`08_reporting/events/`). Item par item de la DoD :

| # | Item DoD v0 | Constat | Cotation |
|---|---|---|---|
| A2-01 | Adapter baseline (`requête → liste ordonnée d'IDs + scores`) | Aucun contrat d'adapter, aucune config de référence | `Non couvert · Bloquant · v0 · Fait` |
| A2-02 | Golden-set v1 figé/versionné (topics stratifiés + qrels gradués) | Aucun topic, aucun qrel, aucun versionnement | `Non couvert · Bloquant · v0 · Fait` |
| A2-03 | Scorer nDCG@R + diagnostics (MAP, R-Precision, Recall@2R, Doc-MRR, Doc-Recall@R), par requête et agrégés | Aucun scorer | `Non couvert · Bloquant · v0 · Fait` |
| A2-04 | Test statistique apparié branché | Absent | `Non couvert · Bloquant · v0 · Fait` |
| A2-05 | ≥ 1 set diagnostique graph-hop opérationnel | Absent (et conditionné par A1-06) | `Non couvert · Bloquant · v0 · Fait` |
| A2-06 | Baseline chiffrée et reproductible (runs immuables, seeds figées) | Aucun run, aucune mesure | `Non couvert · Bloquant · v0 · Fait` |

C'est conforme au statut déclaré (« cadré, non implémenté ») : le constat n'est pas une surprise, c'est la **quantification du reste-à-faire** — l'intégralité de P2.

### Axe A3 — P3 Applicatif : inventaire (hors DoD v0)

**A3-01 — Le chemin RAG de bout en bout est rompu à l'instantané (contra `STATUS.md`).** `Écart majeur · Élevé · hors-v0 · Fait`
Deux ruptures de contrat ingestion→serving : **(a)** le backend filtre les hits sur `payload.chunkId` (`chatService.ts:59`) alors que le pipeline écrit `chunk_id` — tous les hits sont éliminés ; **(b)** le fetch Mongo interroge `find({chunkId: …})` sur la collection `MONGODB_COLLECTION || 'chunks'` (`mongodb.ts:98-101`) — collection inexistante (`LEGIFRANCE` = `documents`, `manifest`) et champ inexistant. Démonstration à l'exécution : POST `/api/v1/chat/streams` → recherche Qdrant OK (log `Qdrant search completed`) puis `WARN "No documents to fetch (empty chunkId list)"`, **zéro part `data-document` émise**. `STATUS.md` (« chemin critique opérationnel ») décrivait l'état antérieur au changement de schéma d'ingestion.
*Preuves :* logs backend 2026-07-17 22:18 ; sortie SSE brute ; payload Qdrant constaté (`chunk_id`, pas de `chunkId`).

**A3-02 — Adaptation serving en cours, non commitée : le pointeur de collection fonctionne.** `Écart mineur · Modéré · hors-v0 · Fait`
`collectionPointer.ts` (nouveau) + boot `server.ts` : lecture de `MURPHY_META.meta_published_collection`, résolution + vérification d'existence de la collection au démarrage. Vérifié au boot réel : `Collection résolue depuis le pointeur publié … 9424808d…`, `Collection Qdrant vérifiée`. Ce chantier traite la moitié « quelle collection ? » du problème ; il ne traite pas encore A3-01.
*Preuves :* diff non commité `backend/` ; logs de boot.

**A3-03 — Health check Qdrant : faux négatif permanent.** `Écart mineur · Faible · hors-v0 · Fait`
`health.ts:53` appelle `GET {QDRANT_URL}/health`, endpoint absent du Qdrant déployé (1.16.3 → 404). Le health global rapporte `degraded` alors que Qdrant répond (la recherche fonctionne dans la même minute).
*Preuves :* `GET /api/v1/health` → `qdrant: down, HTTP 404` ; recherche OK dans les logs.

**A3-04 — Tests backend : 2 suites sur 3 ne compilent plus ; couverture réelle 3,55 %.** `Écart majeur · Modéré · hors-v0 · Fait`
`ragService.test.ts` et `chat.test.ts` référencent des exports disparus (`buildRagContext`, `MammouthProvider`) → échec TS. 4 tests passent (1 suite). Couverture mesurée : **3,55 % lignes / 2,81 % branches**, contre des seuils déclarés de 65/40 — `npm test` échoue donc mécaniquement. `type-check` passe. Le « Tests : Jest avec seuils ✅ » de `STATUS.md` ne correspond plus au réel.
*Preuves :* sortie `npx jest --coverage` (2026-07-18) ; messages TS2305/TS2339.

**A3-05 — Neo4j : câblé à l'ingestion, pas au serving.** `Conforme · — · hors-v0 · Fait`
Aucun import Neo4j dans `backend/src` (grep négatif) : conforme à `STATUS.md` et à la réserve « enrichissement graphe futur ». À noter pour A2 : le harnais consommera le graphe **directement**, pas via le backend — l'absence côté serving ne bloque pas la v0.

### Axe A5 — Conformité ADR & cohérence documentaire

**A5-01 — ADR-018 « ECLI primaire » : le code fait l'inverse (et le mesure).** `Écart majeur · Modéré · v0 · Fait`
L'ADR dit : « ECLI = identifiant stable primaire ; IDs internes DILA = clés techniques de partition ». Le code fait : **ID DILA primaire partout** (`decision:JURITEXT…` = clé Mongo/Qdrant/Neo4j), ECLI simple champ de métadonnées — rempli à 153/352 sur le corpus (jade 23 %, capp/inca 0 %). Le choix du code est défendable (l'ECLI manque sur près de 6 décisions sur 10) mais il contredit la lettre de la décision actée. **À trancher par mise à jour d'ADR-018** (acter « DILA primaire, ECLI attribut de correspondance ») ou par un plan de remontée de l'ECLI.
*Preuves :* `identifiers.py:103-141` (DecisionId) ; mesure ECLI (A1-03) ; ADR-018.

**A5-02 — Décisions structurantes implémentées sans ADR.** `Écart mineur · Modéré · v0 · Fait`
Trois mécanismes qui engagent l'architecture n'apparaissent dans aucun ADR 001-020 : **(a)** collection Qdrant dérivée du fingerprint de config + **pointeur de collection publiée** (`meta_published_collection`, publication réservée aux runs `ok`) — c'est le socle de l'A/B et du contrat P1→P3 ; **(b)** `owner_id` (multi-tenancy) présent dans toutes les clés des 3 BDD ; **(c)** normalisation `v1` entrant dans le hash. Le cadrage (§A5) demandait précisément de repérer les décisions « tranchées implicitement dans le code sans ADR » : ce sont celles-là.
*Preuves :* `fingerprint.py`, `published_collection_repository.py`, `parameters.yml` (formatting.normalization), clés `owner_id` dans les 3 repos.

**A5-03 — Dérives documentaires : confirmées et bornées.** `Écart mineur · Faible · hors-v0 · Fait`
(a) `PROGRAM` §3 énonce toujours « scorer nDCG@k / Recall@k » (ligne 91) — ADR-007 (nDCG@R) fait foi, comme le cadrage l'a posé. (b) `PROGRAM` §6 liste comme ⬜ ouvertes des décisions **toutes tranchées** par ADR-001–010 ; §2.1 marque P4 « à confirmer » alors qu'ADR-001 est acté. (c) `ROADMAP.md` et `BETA.md` subsistent dans `docs/to-sort-out/` (archivage prévu, non fait). (d) `STATUS.md` est daté d'avant la refonte ingestion (cf. A3-01, A3-04). (e) `CLAUDE.md` décrit `chunk_size: 128`, Mongo `LEGIFRANCE.chunks` et un `ragcore` « externe au dépôt » — le réel est 384, `documents`, et `ragcore` vendored dans `data/src/`. (f) `ETAT.md` (data) s'auto-déclare périssable et l'est (18 090 chunks annoncés, 18 023 constatés).
*Preuves :* fichiers cités, lignes vérifiées.

**A5-04 — ADR-020 (tri-base, stateless, fail-fast) : conforme.** `Conforme · — · v0 · Fait`
Mongo porte le texte intégral ; Qdrant les vecteurs + métadonnées (Cosine/768) ; Neo4j des références **sans texte** — seule exception : les 68 nœuds `Unknown` portent `text` = le libellé brut de la cible non résolue, ce qui est la doctrine documentée du type (la citation existe, son identité manque), pas une violation. Backend stateless (seule la dernière question) et fail-fast (aucun retry) : vérifié dans `chatService.ts`/`ragService.ts`.

**A5-05 — ADR-002/003/004 (périmètre, séquençage, unité document) : conformes, sous réserve d'A1-01.** `Conforme · — · v0 · Fait`
Les 5 bases juris + LEGI sont câblées (enum `SourceName`, tables de rôles couvrant les 3 racines XML dont le partage CASS/INCA) et présentes en base. ADR-004 : unité = décision en juris, article en LEGI — vérifié (A1-04). ADR-005/006/007/008/009/010 : **sans objet dans le code** (aucun harnais à confronter) ; aucune divergence, aucune mise en œuvre.

---

## 3. Delta v0 — backlog priorisé de l'incrément final

Le périmètre v0 restant, ordonné par gravité puis par dépendance :

1. **[Bloquant] Implémenter P2 en entier** (A2-01 → A2-06, dans l'ordre de dépendance) :
   1. contrat d'adapter + adapter de la config baseline (Qdrant dense actuel) ;
   2. schéma topics/qrels JSONL canonique (ADR-008) + projections TREC ;
   3. golden-set v1 : topics stratifiés par les 4 types d'action (ADR-009), qrels gradués par la cascade Q1-Q3 (ADR-005), pooling + amorçage citations relu (garde-fou circularité) ;
   4. scorer nDCG@R + diagnostics (ADR-007), agrégation chunk→document `max`/premier-rang (ADR-006) ;
   5. test apparié dans le rapport ;
   6. set diagnostique graph-hop ;
   7. baseline chiffrée, run immuable, seeds figées.
2. **[Élevé] Passe de résolution des relations pendantes** (A1-06) : 19 032 pendantes → graphe de citations exploitable. Prérequis des qrels citation-minées et du graph-hop (items 1.3 et 1.6).
3. **[Élevé] Trancher la volumétrie v0 par ADR** (A1-01) : l'échantillon actuel (CAPP=1, INCA=1) suffit-il à une baseline « mesurable », ou la v0 exige-t-elle les 5 bases en volume ? La DoD est muette ; la décision conditionne le golden-set.
4. **[Modéré] Statuer l'identité chunk** (A4-02) : amender `CADRAGE_evaluation` §2 (chunk_id porté par Qdrant seul, doc_id partagé) ou faire porter le chunk_id aux autres bases. Une phrase d'ADR suffit.
5. **[Modéré] Mettre à jour ADR-018** (A5-01) : acter la pratique réelle (DILA primaire, ECLI attribut) ou planifier la remontée ECLI.
6. **[Modéré] Corriger le typage JADE** (`type_document: "Texte"` → valeur décisionnelle, A1-03a).

**Hors delta v0** (ne gate pas la version — à traiter pour l'alpha) : réparation du contrat serving (A3-01 : lire `chunk_id`, fetch Mongo par `identifier` sur `documents`), health check Qdrant (A3-03), remise au vert des tests backend (A3-04), commit du chantier pointeur (A3-02), nettoyage documentaire (A5-03).

---

## 4. Écarts code ↔ ADR (livrable 4)

| Réf. | Décision actée | Réel constaté | Action proposée |
|---|---|---|---|
| ADR-018 | ECLI identifiant primaire, DILA clé technique | DILA identifiant primaire partout ; ECLI métadonnée remplie à 43 % | Amender ADR-018 (constat A5-01) |
| ADR 001–010 vs `PROGRAM` §6 | Décisions tranchées | `PROGRAM` §6/§2.1 les affiche encore ouvertes | Mise à jour `PROGRAM` (A5-03b) |
| ADR-007 vs `PROGRAM` §3 | nDCG@R, rejet des k fixes | `PROGRAM` §3 mentionne nDCG@k | Mise à jour `PROGRAM` (déjà identifié au cadrage) |
| — (aucun ADR) | — | Fingerprint→collection + pointeur publié ; `owner_id` ; normalisation hashée | Rédiger 1 à 3 ADR courts (A5-02) |
| ADR-020 | Neo4j sans texte | 68 nœuds `Unknown` portent le libellé brut | Aucune — doctrine documentée du type |

---

## Annexe A — Méthode et échantillonnage (§6.2 du cadrage)

- **Cross-DB (A4)** : scroll exhaustif de la collection Qdrant (18 023 points), extraction des 811 identifiants distincts, tirage `random.seed(42)` de ≤ 5 identifiants par famille de préfixe (5 familles, 22 identifiants), vérification de présence dans Mongo (`count_documents`) et Neo4j (`MATCH (n {identifier: $i})`). Scripts : `docs/product/audit/audit_a4.py`, `docs/product/audit/audit_a1.py` — réexécutables tels quels contre l'instantané (les identifiants de connexion viennent de `.env.dev`).
- **Volumétrie et remplissage (A1)** : exhaustifs, pas échantillonnés (1 121 documents, 18 023 chunks, 2 916 XML) — le corpus le permettait.
- **Tests** : `pytest` ragcore (280 tests) et `npx jest --coverage` backend exécutés le 2026-07-18 sur l'instantané.
- **Serving (A3)** : test boîte noire `POST /api/v1/chat/streams` + logs conteneur `backend`, stack compose dev complète démarrée par le commanditaire.

## Annexe B — Remplissage réel par source (extrait, champs non vides / total)

| Champ | capp (1) | cass (92) | inca (1) | jade (256) | constit (2) |
|---|---|---|---|---|---|
| `ecli` | 0 | 92 | 0 | 59 | 2 |
| `type_document` | 1 (ARRET) | 92 (ARRET) | 1 (ARRET) | 256 (**Texte**) | 2 (QPC) |
| `date_decision` | 1 | 92 | 1 | 256 | 2 |
| `numero` | 1 | 92 | 0¹ | 256 | 2 |
| `president` | 0 | 90 | 1 | 192 | 0 |
| `avocats` | 0 | 88 | 0 | 252 | 0 |
| `solution` | 0 | 92 | 1 | 0 | 2 |

¹ INCA porte `numero_affaire` sans `numero`. LEGI (769 docs) : `title` 769/769 ; champs de version (`date_debut`/`date_fin`/`statut`) 482/769 (articles + textes ; absents des sections).

## Annexe C — Volumétrie constatée

| | XML source | Docs Mongo | Docs avec vecteurs | Chunks Qdrant |
|---|---|---|---|---|
| LEGI | 2 564 | 769 | 459² | 3 303 |
| JADE | 256 | 256 | 256 | 11 631 |
| CASS | 92 | 92 | 92 | ~2 950³ |
| CAPP | 1 | 1 | 1 | ³ |
| INCA | 1 | 1 | 1 | ³ |
| CONSTIT | 2 | 2 | 2 | 71 |
| **Total** | **2 916** | **1 121** | **811** | **18 023** |

² 384 articles + 75 textes à contenu non vide (287 sections et 23 textes vides non embarqués — comportement attendu).
³ CASS/CAPP/INCA partagent le préfixe `JURITEXT` : 3 018 chunks au total pour le judiciaire.
