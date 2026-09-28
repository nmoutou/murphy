# Améliorations de qualité

Journal des améliorations faites et des pistes écartées. Une amélioration listée ici
n'est pas refaite. Les lots précédents (BE-01…18, FE-01…11, TR-01…07, DA-01…06) sont
dans l'historique git : `git show 9c32a83^:docs/pilotage/corrections/`.

## Faites

### 2026-09-28 — lecture des erreurs et modale testées (chantier 5, lot 2)

- **Fichiers** : `frontend/src/__tests__/lib/chatErrorStage.test.ts`,
  `frontend/src/__tests__/components/chat/ErrorDialog.test.tsx` (nouveaux),
  `frontend/src/__tests__/setup.ts` ; `frontend/package.json`, `package-lock.json` ;
  README technique du frontend, `chantiers.md`.
- **Catégorie** : tests, dépendances.
- **Fait** :
  - `readErrorStage` (9 tests) : `connection` sur une erreur du socket, chaque étape
    de `CHAT_ERROR_STAGES` relue telle que le backend la sérialise, `internal` sur un
    texte non JSON, un JSON sans `stage` ou une étape inconnue ;
  - `ErrorDialog` (9 tests) : ouvert et nommé par son titre, le message de chacune des
    six étapes avec l'invite à réessayer, « Fermer » et Échap (`cancel`) qui préviennent
    le parent sans que le dialogue se ferme seul, fermeture du `<dialog>` natif au
    démontage ;
  - `setup.ts` simule `showModal` et `close`, absents de jsdom, uniquement s'ils
    manquent ;
  - **deux copies de React** : le lockfile gardait `react`/`react-dom` 19.2.4 dans
    `frontend/node_modules` et 19.3.0 à la racine, installés comme pairs de `next`,
    `swr` (via `@ai-sdk/react`), `react-markdown` et Testing Library. Next rend l'app
    avec son React embarqué et masquait l'écart ; Vitest chargeait les deux copies
    (« Cannot read properties of null (reading 'useRef') »). Le frontend passe à
    `^19.3.0` : une seule copie, 3 paquets retirés du lockfile.
- **Vérification** : `npm run check` vert. Trois mutations, chacune détectée puis
  annulée : sans le `preventDefault` du `cancel`, sans le `close()` au démontage, sans
  la branche `connection` de `readErrorStage`.
- **Écarté** : `npm dedupe` sur tout le dépôt échoue sur un conflit de pairs de jest
  dans le backend, et toucherait bien plus que React.

### 2026-09-28 — Vitest dans le frontend, et le transport WebSocket testé (chantier 5, lot 1)

- **Fichiers** : `frontend/package.json`, `package-lock.json`,
  `frontend/vitest.config.mts`, `frontend/src/__tests__/` (`setup.ts`,
  `fakeWebSocket.ts`, `lib/webSocketChatTransport.test.ts`, `lib/chatSocketUrl.test.ts`) ;
  `package.json` racine (`check`), commentaire de `ci.yml` ; `CLAUDE.md`, READMEs du
  frontend, `chantiers.md`.
- **Catégorie** : tests, outillage.
- **Fait** :
  - `vitest` 5, `jsdom` 29, `@testing-library/react`, `dom`, `user-event` et `jest-dom`
    en dépendances de dev ; `npm test -w frontend` dans `npm run check`, donc la CI ;
  - pas de globals Vitest (imports explicites, aucun type global pour `tsc`), d'où le
    `cleanup` de Testing Library appelé dans `setup.ts` ; pas de plugin React (Vite
    compile le JSX de `tsconfig`) ; config en `.mts`, le `package.json` du frontend
    n'étant pas en ESM ;
  - `FakeWebSocket` joue le backend (ouvrir, envoyer une partie, échouer, fermer) et,
    comme un vrai socket, ne signale `close` qu'une fois, quel que soit le côté qui
    ferme ;
  - 10 tests du transport : envoi de la conversation à l'ouverture, parties dans
    l'ordre, fin propre après `finish` ou `error`, erreur de connexion sur une coupure ou
    une erreur du socket, partie illisible, abort, annulation par le lecteur ; 4 tests
    de `getChatSocketUrl`.
- **Vérification** : `npm run check` vert. Retirer le `socket.close()` qui suit la partie
  finale fait échouer 2 tests ; code restauré.
- **Écarté** : `jsdom` 30 exige Node ≥ 24.15 (poste en 24.13) ; `@vitejs/plugin-react`
  n'apporte que le Fast Refresh.

### 2026-09-28 — verrou ESLint sur la taille et la forme du code (chantier 4, lot 3)

- **Fichiers** : `backend/eslint.config.mjs`, `frontend/eslint.config.mjs` ;
  `backend/src/utils/httpStatus.ts` (nouveau) et ses utilisateurs (`app.ts`,
  `middleware/errorHandler.ts`, `requestLogger.ts`, `security.ts`,
  `streamRateLimiter.ts`, `routes/chat.ts`, `routes/health.ts`) ; frontend
  `SourceItem.tsx`, `Logo.tsx`, `ChatLayout.tsx` ; `CLAUDE.md`, READMEs du backend et du
  frontend, `chantiers.md`.
- **Catégorie** : outillage.
- **Fait** :
  - règles ajoutées aux deux configs : `max-lines` 300 (200 pour les `.tsx` du
    frontend), `max-lines-per-function` 30 (hors lignes vides et commentaires),
    `max-depth` 3, `max-params` 4, `complexity` 10, `no-magic-numbers` (sauf 0, 1, -1,
    index de tableau et valeurs par défaut). Les tests sont exemptés de la longueur de
    fonction et des nombres magiques ;
  - les codes HTTP, redéfinis dans cinq fichiers (`HTTP_TOO_MANY_REQUESTS` deux fois,
    `INTERNAL_ERROR_STATUS` et `HTTP_SERVER_ERROR` pour le même 500), sont nommés une fois
    dans `HTTP_STATUS` ;
  - frontend : `PERCENT` (et le calcul du score sorti du JSX), `EXCHANGE_LENGTH` (une
    question et sa réponse), les proportions du logo.
- **Vérification** : `npm run check` vert. Un fichier d'essai (fonction de 34 lignes,
  fonction à 5 paramètres, nombre `42`) est refusé par les deux lints, puis supprimé.

### 2026-09-28 — composants du frontend sous 30 lignes (chantier 4, lot 2)

- **Fichiers** : `frontend/src/components/ChatBox.tsx`, `frontend/src/hooks/useChatInput.ts`
  (nouveau), `frontend/src/components/ui/Modal.tsx`, `frontend/src/components/MainPanel.tsx` ;
  `docs/technical/frontend/ARCHITECTURE.md`.
- **Catégorie** : lisibilité (taille des fonctions).
- **Fait** :
  - `ChatBox` (53 → 23 lignes) : la saisie et la soumission passent dans
    `useChatInput` ; les boutons deviennent deux petits composants du même fichier,
    `ChatBoxAttach` (pièce jointe, inerte pendant un stream) et `ChatBoxAction`
    (Annuler pendant un stream, Envoyer sinon) ;
  - `Modal` (38) : l'ouverture et la fermeture du `<dialog>` et la touche Échap passent
    dans un hook local `useModalDialog`, gardé dans `Modal.tsx` (un seul utilisateur) ;
  - `MainPanel` (31) : le `ChatBox` est construit une fois (`isDocked={hasMessages}`) au
    lieu d'être écrit deux fois ; le `useCallback` autour de `sendMessage` est retiré
    (`ChatBox` n'est pas mémoïsé).
- **Comportement** : même DOM, mêmes classes, mêmes libellés. `npm run check` vert.

### 2026-09-28 — validation complète des messages de chat, sans `as` (chantier 4, lot 1)

- **Fichiers** : `backend/src/validation/chatRequest.ts`, `backend/src/routes/chat.ts`,
  `backend/src/routes/chatWebSocket.ts`,
  `backend/src/__tests__/validation/chatRequest.test.ts`,
  `docs/technical/backend/ARCHITECTURE.md`.
- **Catégorie** : validation à la frontière / typage.
- **Fait** : `parseChatRequest` passe par `safeValidateUIMessages` de l'AI SDK, avec les
  `appDataPartSchemas` et `appMessageMetadataSchema` du contrat. Toute la forme du message
  est vérifiée (id, chaque type de partie, parties `data-*`, métadonnées `ragTiming`), et
  le type `AppUIMessage[]` sort de la validation : l'assertion `as` disparaît. La fonction
  devient asynchrone ; ses trois appelants l'attendent.
- **Deux pièges du SDK, contournés** :
  - le schéma de métadonnées est appliqué à *tous* les messages, et un message `user`
    n'en a pas. Passé tel quel, il rejetait toute requête : le backend le rend
    `.optional()` ;
  - le message d'une `TypeValidationError` recopie toute la valeur reçue, donc la
    conversation. Les problèmes sont reconstruits depuis les issues zod de la cause
    (champ + message du schéma). Un test vérifie que la question n'apparaît dans aucune
    erreur.
- **Tests** : 6 cas ajoutés (conversation de suivi avec sources, message sans `id`,
  score non numérique, partie `data-*` non déclarée, métadonnées invalides, pas d'écho).
  `npm run check` vert : backend 17 suites, 122 tests.
- **Reste à faire, à la main** : sur la stack `serve`, poser deux questions de suite.
  La seconde renvoie la première réponse et ses sources, qui doivent passer.

### 2026-09-27 — verrou ruff : complexité et nombre de paramètres (chantier 3, lot 6)

- **Fichiers** : `data/pyproject.toml`, `orchestration/kedro/nodes/compute_idempotence.py`
  et `nuke_all.py` (`noqa` retirés), tests `test_mongo_pending_repository.py` et
  `test_resolve_relations.py` ; `docs/pilotage/WIP/chantiers.md`.
- **Catégorie** : outillage.
- **Fait** : `C901` sélectionné (`max-complexity = 10`) et `lint.pylint.max-args = 4`.
  Les nœuds Kedro sont exemptés de `PLR0913` par `per-file-ignores` (leur signature est
  le DAG), ce qui rend leurs `noqa` inutiles ; trois façades gardent un `noqa`
  justifié (`build_event`, `RunSummary.of`, `WorkerTelemetryFactory.__init__`). Les
  3 fonctions de test au-delà de 4 paramètres sont corrigées (`first_seen` jamais
  utilisé retiré de `_pending` ; service construit dans le test plutôt qu'injecté).
- **Pourquoi** : sans verrou, les fonctions reviennent à 6 paramètres au premier ajout.
- **Vérification** : `ruff check .` vert ; une fonction d'essai à 5 paramètres est
  refusée (`PLR0913`) puis retirée ; `mypy` vert ; 329 tests réussis ; intégration Mongo
  (pendantes) : 8 réussis. Bilan du chantier 3 dans `chantiers.md`.

### 2026-09-27 — `orchestration/kedro/` : nœuds et pipeline découpés (chantier 3, lot 5)

- **Fichiers** : `orchestration/kedro/nodes/compute_idempotence.py`, `nuke_all.py`,
  `cleanup.py`, `connect.py`, `orchestration/kedro/pipeline.py`, `workload.py`,
  `assembly.py`, `adapters/embedding/openai_embedder.py`, nouveau
  `adapters/embedding/served_model.py` (sous `data/src/ragcore/`) ; tests
  `test_workload.py`, `test_openai_embedder.py`.
- **Catégorie** : taille des fonctions et des fichiers / duplication / paramètres.
- **Fait** :
  - `compute_idempotence_node` (115 lignes, la plus longue de `data/`) : signature
    inchangée (c'est le DAG), corps à ~20 lignes. Les deux branches d'exclusion
    (`ValidationError`, `ParseError`), identiques au motif près, passent par un seul
    `_ParseSite.exclude` paramétré par un `_Rejection` (raison, log, forme de la raison
    au manifeste) ; `declare_signals`, `decide_operation`, `_apply_cursor`.
  - `create_ingestion_pipeline` (84) : une fonction par nœud (`_cleanup()`…), la
    publique ne fait qu'assembler.
  - `nuke_all_node` (44), `cleanup_node` (35), `connect_node` (31) : `_assert_dev_environment`,
    `_drop_mongo`, `_emit_nuked`, `_clear`, `_emit`.
  - `build_document_workload` : 6 paramètres (`noqa`) → 4, via `WorkloadSteps(chunker,
    embedder, extractor)`, que `assembly.ProcessingStack` réutilise ; le cache de use
    case par worker devient `_UseCasePerWorker`, l'extraction `_extract`.
  - `assert_service_serves_model` passe dans `served_model.py` : `openai_embedder.py`
    avait franchi 300 lignes (305) avec `EmbeddingTransport` au lot 4.
- **Pourquoi** : les dernières fonctions longues de `data/`.
- **Vérification** : `ruff`, `ruff format --check`, `mypy` verts ; 329 tests réussis ;
  `deepcopy` des `HOOKS` et `kedro registry list` OK. **Plus aucune fonction de plus de
  30 lignes ni aucun fichier de plus de 300 lignes dans `data/src` (hors tests).**

### 2026-09-27 — adaptateurs : Neo4j, index Mongo, embedder (chantier 3, lot 4)

- **Fichiers** : `adapters/storage/neo4j/graph_repository.py`, nouveau
  `adapters/storage/neo4j/node_properties.py`, `adapters/storage/mongo/schemas.py`,
  `adapters/embedding/openai_embedder.py`, `adapters/embedding/__init__.py`,
  `orchestration/kedro/assembly.py`, `run_plan.py`, `run_parameters.py` (sous
  `data/src/ragcore/`) ; tests `test_openai_embedder.py`, `test_ports_conformance.py`.
- **Catégorie** : taille de fichier et de fonctions / nombre de paramètres.
- **Fait** :
  - Neo4j : `NodeHydration`, les citations, le label (`node_label`) et les propriétés
    du nœud (`node_props`) passent dans `node_properties.py` ; les requêtes deviennent
    des constantes nommées (`_MERGE_NODE`, `_COUNT_INCOMING`, `_DETACH_DELETE_NODE`,
    `_DEHYDRATE_NODE`). `merge_document_node` (34 lignes) et `compensate_document_node`
    (33) tombent à quelques lignes ; `graph_repository.py` passe de 352 à 268 lignes.
  - Mongo : les index sont des constantes par collection (`_DATA_INDEXES`,
    `_META_INDEXES`) posées par une seule boucle ; `ensure_meta_indexes` (55 lignes)
    tient en une ligne.
  - `OpenAIEmbedder.__init__` : 5 paramètres → 2, `EmbeddingConfig` (le modèle, hashé)
    et `EmbeddingTransport` (l'accès au service : URL, clé, lot — de l'infra).
- **Pourquoi** : deux des fonctions longues, un fichier au-dessus de 300 lignes et un
  constructeur à 5 paramètres.
- **Vérification** : `ruff`, `ruff format --check`, `mypy` verts ; 329 tests réussis ;
  **tests d'intégration** Neo4j et Mongo (testcontainers) : 28 réussis — les requêtes
  Cypher refactorées se comportent à l'identique sur un vrai serveur.

### 2026-09-27 — `sources/generic/parser.py` découpé (chantier 3, lot 3)

- **Fichiers** : `sources/generic/parser.py`, nouveaux `tree.py`, `structure.py`,
  `unconfigured.py`, `chunking.py` (sous `data/src/ragcore/`) ;
  `docs/technical/data/reference/sources.md`.
- **Catégorie** : taille de fichier et de fonctions / complexité / imbrication /
  nombre de paramètres.
- **Fait** :
  - `tree.py` : la relecture de l'arbre transcrit (`walk`, `find_all`, `first`,
    `text_of`, `holders`…), plus `nested(tree, containers, tags)`, qui aplatit les
    boucles conteneur → parent → balise → nœud répétées trois fois.
  - `structure.py` : `read_references` (ex-`_references`, 43 lignes, C901 = 12,
    cinq niveaux d'imbrication) découpé en `_declared_links`, `_structural_links`,
    `_version_links` ; `read_context`.
  - `unconfigured.py` : la cascade des trois portes. `UnconfiguredRouting` porte
    l'identifiant, les métadonnées et références du document, et les signaux
    (balises, clés, racines) ; `_route_values` passe de 6 paramètres (`noqa`) à 3, son
    motif attribut/feuille factorisé dans `_route_value`.
  - `parser.py` : `parse` délègue à `_interpret` et `_document` ; `_metadata` et
    `_text_blocks` perdent leurs cinq niveaux d'imbrication (`_meta_leaves`,
    `_is_collectable`, compréhension).
  - `chunking._chunk` : 6 paramètres (`noqa`) → 3, via un `_Span`.
- **Pourquoi** : `parser.py` faisait 540 lignes, avec la seule fonction de `data/` que
  ruff jugeait trop complexe.
- **Vérification** : `ruff` (dont `C901` sur `sources/`), `ruff format --check`, `mypy`
  verts ; 329 tests réussis, dont les golden (`test_legi_corpus`, `test_role_table`,
  `test_parser`) : mêmes documents, mêmes métadonnées, mêmes références. `parser.py` :
  540 → 276 lignes ; plus aucune fonction de plus de 30 lignes dans `sources/generic/`.

### 2026-09-27 — `core/links/extraction.py` découpé (chantier 3, lot 2)

- **Fichiers** : `core/links/extraction.py`, nouveaux `core/links/versions.py`,
  `subject.py`, `table.py`, `citations.py`, `core/links/__init__.py` (sous
  `data/src/ragcore/`) ; `sources/generic/relations.py` ;
  `sources/juri/tests/test_juri.py`.
- **Catégorie** : taille de fichier et de fonctions / nombre de paramètres.
- **Fait** :
  - `versions.py` : la chaîne temporelle (`version_chain`, ex-`_version_chain` de
    67 lignes, découpée en `_living_sorted`, `_neighbour_edges`, `_stillborn_branches`,
    `_edge_if_stillborn`), avec `VERSION_KIND` et `STILLBORN_SUFFIX` (toujours exportés
    par `core.links`).
  - `subject.py` : `LinkSubject` (ex-`_Subject`, désormais public) porte la seule
    fabrique de `Relation` (`relation(source, target, verb, metadata)`, ex-`_relation`
    à 5 paramètres).
  - `extraction.py` : un `_Extraction(table, subject, unknowns)` porte `identifier`,
    `from_reference` (ex-43 lignes et `noqa: PLR0911`, découpé en `_heuristic` et
    `_typed`) et `from_ancestor`. `extract_links(references, ancestors, table, subject)`
    passe de 6 paramètres (`noqa: PLR0913`) à 4.
  - `table.py` (`LinkTable`) et `citations.py` (`citation_from`) sortent pour ramener
    `extraction.py` de 544 à 300 lignes.
- **Pourquoi** : le plus gros fichier de `data/` et deux des fonctions les plus longues.
- **Vérification** : `ruff`, `ruff format --check`, `mypy` verts ; 329 tests réussis,
  dont les golden sur le corpus de fixtures (`test_legi_corpus`, `test_relations`) :
  mêmes arêtes, mêmes inconnus, mêmes citations. Plus aucune fonction de plus de
  30 lignes dans `core/links/`.

### 2026-09-27 — `application/` : fonctions longues découpées (chantier 3, lot 1)

- **Fichiers** : `application/saga.py`, `ingest_document.py`, `resolve_relations.py`,
  `ingestion_runner.py`, `orchestration/kedro/stores.py`, `assembly.py` (sous
  `data/src/ragcore/`) ; tests `test_ingest_document.py`, `test_workload.py`.
- **Catégorie** : taille des fonctions / nombre de paramètres.
- **Fait** :
  - `SagaExecutor.execute` (65 lignes) → `_announce`, `_compensate_all`,
    `_compensate_one`, `_report` ; l'exception d'origine est relancée par un `raise` nu.
  - `IngestDocumentUseCase.execute` (55) → `_saga_steps` (qui garde le commentaire sur
    le trou de l'UPDATE, en docstring) et `_record`. `__init__` passe de 5 à 2
    paramètres : `IngestionStores` (4 dépôts typés par leurs ports) remplace aussi
    `orchestration/kedro/stores.DocumentStores`, son jumeau concret.
  - `ResolveRelationsService.execute` (42) et `_promote` (36) → `_record_pending`,
    `_announce_written`, `_emit_promoted`.
  - `IngestionRunner._run_shard` (40, trois niveaux d'imbrication) → `_process`,
    `_declare_failure`, `_close_worker` (avec son commentaire d'ordre) ; un
    `_ShardResult` remplace le tuple à 4 éléments.
- **Pourquoi** : 4 des 20 fonctions de plus de 30 lignes de `data/`.
- **Vérification** : `ruff`, `ruff format --check`, `mypy` verts ; 329 tests réussis ;
  plus aucune fonction de plus de 30 lignes dans `application/`.

### 2026-09-27 — l'état du run dans une `RunSession` (chantier 1, lot 5)

- **Fichiers** : nouveau `orchestration/kedro/run_session.py`, `orchestration/kedro/hooks.py`
  (sous `data/src/ragcore/`) ; nouveau `tests/unit/orchestration/test_run_session.py` ;
  trois docstrings qui citaient `hooks.py` (`adapters/config/settings.py`,
  `test_ports_conformance.py`, `test_run_summary.py`) ;
  `docs/technical/data/reference/pipeline.md`, `docs/pilotage/WIP/chantiers.md`.
- **Catégorie** : structure / typage.
- **Fait** : `RunSession`, dataclass figée sans champ optionnel (contexte, télémétrie,
  agrégat, dossier des stats, dépôt des bilans, publieur, tracker, embedder, runtime),
  porte `emit_lifecycle_event` et `close(status)` (raccourcis → drain → bilan →
  publication si `ok` → tracker). Le hook ne garde que son runtime et
  `_session: RunSession | None` : ses sept attributs optionnels et leurs vérifications
  `is None` disparaissent ; sans session (assemblage raté), la fin de run ne fait que
  fermer le runtime.
- **Effet de bord voulu** : le run de tracking s'ouvre avec la session, après la
  vérification du modèle servi par TEI et la création des index. Un TEI qui ne sert pas
  le bon modèle n'ouvre donc plus de run MLflow que rien ne refermerait.
- **Pourquoi** : `hooks.py` restait à 393 lignes après le lot 4, dont l'essentiel en état
  du run et vérifications de `None`.
- **Vérification** : `ruff`, `ruff format --check`, `mypy` verts ; 329 tests réussis
  (5 nouveaux sur la clôture : run complet persisté/publié/tracé, run cassé non publié,
  audit perdu au drain ⇒ `degraded` et pas de publication, raccourcis déclarés sur un
  run cassé, tracker refermé même si `log_summary` échoue) ; `deepcopy` des `HOOKS` et
  `kedro registry list` OK. `hooks.py` : 393 → 210 lignes ; `run_session.py` : 227.
  Chantier 1 terminé.

### 2026-09-27 — cycle de vie du hook dédoublonné (chantier 1, lot 4)

- **Fichiers** : `orchestration/kedro/hooks.py`, `orchestration/kedro/nodes/report.py`
  (docstrings), `tests/unit/orchestration/test_summary_absorbs_workers.py` (sous
  `data/src/ragcore/`) ; `data/conf/base/catalog.yml` (commentaire) ;
  `docs/technical/data/reference/pipeline.md` et `telemetrie.md`.
- **Catégorie** : duplication / couplage des tests.
- **Fait** :
  - `_emit_run_event` remplace les trois `build_event` quasi identiques (démarré,
    terminé, échoué ; mêmes charges utiles).
  - `_close_run(status)` : la séquence de clôture (raccourcis → drain → bilan →
    publication si `ok` → tracker → runtime) écrite une fois pour `after_pipeline_run`
    et `on_pipeline_error` ; ses commentaires d'ordre aussi. Statut typé `RunStatus`
    (un `type: ignore` en moins).
  - Le `run_stats_sink` du catalogue est l'agrégateur du run lui-même
    (`RunStatsAggregator.absorb` respecte déjà `RunStatsSink`) : `TelemetryHooks.absorb`
    disparaît, et les tests passent l'agrégateur à `report_node` au lieu d'écrire
    `hooks._aggregator`.
- **Pourquoi** : les deux fins de run répétaient la même séquence et ses justifications ;
  les tests du fil `report` → bilan dépendaient d'un attribut privé du hook.
- **Vérification** : `ruff`, `ruff format --check`, `mypy` verts ; 324 tests réussis (le
  test « hook sans agrégateur » n'a plus d'objet) ; `deepcopy` des `HOOKS` OK.
  `hooks.py` : 450 → 393 lignes, toutes ses fonctions sous 30 lignes. Encore au-dessus
  de 300 : l'état du run part dans un `RunSession` au lot 5.

### 2026-09-27 — assemblage du run extrait du hook (chantier 1, lot 3)

- **Fichiers** : nouveaux `orchestration/kedro/run_plan.py`, `stores.py`, `assembly.py`
  (sous `data/src/ragcore/`) ; `orchestration/kedro/hooks.py` ; docstring de
  `workload.py` ; nouveaux `tests/unit/orchestration/test_run_plan.py` et
  `test_assembly.py` ; `docs/technical/data/reference/pipeline.md`.
- **Catégorie** : structure / duplication / typage.
- **Fait** :
  - `run_plan.plan_run` rend un `RunPlan` figé (workflow, collection, sources, owner,
    hydratation Neo4j, interrupteur d'embedding ; `is_full_run` et `context_source` en
    propriétés) : ce que le hook dérivait en plusieurs endroits, dérivé une fois.
  - `stores.open_clients` est la seule création des clients Mongo/Neo4j/Qdrant ; le hook
    et chaque worker l'appellent (le code est partagé, pas les instances, §11). Les
    dépôts sont regroupés en `DocumentStores` (ce que l'ingestion écrit, hook et
    workers) et `MetaStores`.
  - `assembly.prepare_embedder` : **une seule** branche `match` sur le provider (vérifier
    puis construire), au lieu de deux. `build_processing_stack` et `build_runner`
    (4 paramètres au lieu de 7, sans `noqa: PLR0913` ni `assert`).
  - Embedder typé `BaseEmbedder` ; le `getattr(…, "truncations", 0)` devient un
    `isinstance` sur le Protocol `ReportsTruncations` ; le `type: ignore[arg-type]` du
    workload disparaît.
  - `before_pipeline_run` : 180 lignes de code et un `noqa: PLR0915` → 5 méthodes de
    moins de 30 lignes ; le catalogue est rempli par une boucle sur un dict.
- **Effet de bord voulu** : une source inconnue (`--params source=cas`) échoue désormais
  avant l'ouverture du tracker et des clients, et non après.
- **Pourquoi** : `before_pipeline_run` enchaînait douze responsabilités ; la création des
  clients et le choix de l'embedder étaient écrits deux fois.
- **Vérification** : `ruff`, `ruff format --check`, `mypy` verts ; 325 tests réussis
  (10 nouveaux, sans base ni réseau : le client Qdrant, qui interroge la version du
  serveur dès sa construction, est remplacé) ; `deepcopy` des `HOOKS` et
  `kedro registry list` OK. `hooks.py` : 736 → 450 lignes ; plus aucune fonction de plus
  de 30 lignes dans `hooks.py`, `run_plan.py`, `stores.py`, `assembly.py`.

### 2026-09-27 — publication du pointeur extraite du hook (chantier 1, lot 2)

- **Fichiers** : nouveau `application/publish_collection.py`, `orchestration/kedro/hooks.py`
  (sous `data/src/ragcore/`) ; `tests/unit/orchestration/test_publish_condition.py`
  devenu `tests/unit/application/test_publish_collection.py` ; nouveau
  `tests/unit/orchestration/test_hooks_unwired.py` ;
  `docs/technical/data/reference/pipeline.md`.
- **Catégorie** : structure / testabilité.
- **Fait** : `CollectionPublisher(repo, collection_name, is_full_run=…)` porte la règle
  de publication (ADR-039) : `publish_if_complete(summary)` ne publie que sur un bilan
  `ok` et si `may_publish` l'autorise ; il rend le pointeur publié ou `None`. Mêmes logs
  et mêmes docstrings que `_publish_collection` / `_contract_allows_publication`, retirés
  du hook. Dans le hook, `_published_repo`, `_qdrant_collection` et `_is_full_run`
  deviennent un seul `_publisher`. La règle vit dans `application/` (pas de dépendance
  à Kedro), et non dans `orchestration/kedro/publication.py` comme prévu au départ.
- **Pourquoi** : une règle métier n'a rien à faire dans le câblage Kedro ; ses 9 tests
  écrivaient trois attributs privés du hook pour l'atteindre. Ils visent maintenant
  `CollectionPublisher` directement.
- **Vérification** : `ruff`, `ruff format --check`, `mypy` verts ; 315 tests réussis
  (les 9 cas de publication conservés, 1 test du pointeur rendu, 2 tests d'un hook jamais
  câblé qui finit ou échoue sans exploser) ; `deepcopy` des `HOOKS` OK.
  `hooks.py` : 801 → 736 lignes.

### 2026-09-27 — `hooks.py` : paramètres du run extraits (chantier 1, lot 1)

- **Fichiers** : `orchestration/kedro/hooks.py`, nouveau `orchestration/kedro/run_parameters.py`
  (sous `data/src/ragcore/`) ; imports de `test_load_parameters.py`,
  `test_resolve_sources.py`, `golden/test_fingerprint.py` ; deux docstrings qui citaient
  les anciens noms (`compute_idempotence.py`, `graph_repository.py`) ;
  `docs/technical/data/reference/pipeline.md` et `configuration.md`.
- **Catégorie** : structure (taille de fichier).
- **Fait** : déplacement pur de `load_parameters`, `build_workflow_config`,
  `resolve_embedding_enabled`, `resolve_node_hydration` et `resolve_sources`, devenues
  publiques (sans `_`) puisqu'importées d'ailleurs. Code et docstrings inchangés.
- **Pourquoi** : premier des 4 lots qui ramènent `hooks.py` (960 lignes) sous 300 ; ces
  fonctions pures sur `params` n'ont rien à voir avec le cycle de vie du run.
- **Vérification** : `ruff`, `ruff format --check`, `mypy` verts ; 313 tests réussis,
  dont le cliquet `golden/test_fingerprint.py` (collection dérivée inchangée) ;
  `deepcopy` des `HOOKS` de `data/settings.py` OK. `hooks.py` : 960 → 801 lignes.

### 2026-09-27 — `data/` : règle ruff `BLE` activée (chantier 2, lot 2)

- **Fichiers** : `data/pyproject.toml`, `adapters/telemetry/registry_aware.py`,
  `application/saga.py`, `application/ingestion_runner.py` (sous `data/src/ragcore/`),
  `docs/pilotage/WIP/chantiers.md`.
- **Catégorie** : gestion d'erreurs / outillage.
- **Fait** : `"BLE"` (flake8-blind-except) ajouté à `[tool.ruff.lint] select`. Les
  5 frontières voulues portent un `# noqa: BLE001 — <raison>` : les 3 de la télémétrie
  (une panne de backend ne casse pas le run, elle est comptée), la compensation de la
  saga (un échec n'interrompt pas les suivantes) et le runner (le document est perdu,
  pas le run).
- **Pourquoi** : sans la règle, rien n'empêchait un nouvel `except Exception` aveugle ;
  les `noqa: BLE001` existants étaient sans effet.
- **Vérification** : `ruff check .` vert ; un `except Exception: pass` d'essai est
  refusé (`BLE001`, code de sortie 1) puis retiré. `ruff format --check`, `mypy` verts ;
  313 tests réussis.

### 2026-09-27 — `data/` : 4 `except Exception` restreints (chantier 2, lot 1)

- **Fichiers** : `core/links/extraction.py`, `sources/generic/parser.py`,
  `orchestration/kedro/hooks.py`, `orchestration/kedro/nodes/compute_idempotence.py`,
  `core/exceptions.py` (commentaire) ; tests : `sources/legi/tests/test_relations.py`,
  `sources/legi/tests/test_parser.py`, `tests/unit/core/test_exceptions.py`
  (docstring), nouveaux `tests/unit/orchestration/test_load_parameters.py` et
  `test_compute_idempotence.py` (chemins relatifs à `data/src/ragcore/`).
- **Catégorie** : gestion d'erreurs.
- **Fait** :
  - `extraction._identifier` : `except pydantic.ValidationError`. Seul un id mal formé
    est déclaré `identifiant` inconnu ; un bug de `identifier_for` remonte.
  - `GenericParser._identifier` : `except PydanticValidationError` (import aliasé, le nom
    est pris par l'erreur métier) relayé en `ValidationError` métier ; le
    `except ValidationError: raise` devenu inutile disparaît. Un bug de la table devient
    une `ParseError` via la frontière de `parse`, plus un refus métier.
  - `hooks.py` : le chargement de `parameters.yml` passe dans `_load_parameters`, qui ne
    traduit que la `DatasetError` de Kedro. Testable sans `.env.dev` ; prépare le
    chantier 1.
  - `compute_idempotence_node` : `except ParseError`, le contrat de `BaseParser`.
    **Changement de comportement** : une exception hors contrat (le `ValueError` de
    `RoutingParser` pour un document non routable) arrête le run au lieu d'exclure le
    document en `parse_error`. C'est ce qu'annonçait la docstring de
    `composite._unroutable` (« il faut le savoir tout de suite »).
- **Pourquoi** : ces captures déguisaient des bugs en cas prévus (id illisible, refus
  métier, config illisible, document illisible).
- **Vérification** : 7 nouveaux tests, dont 4 qui échouaient avant le correctif
  (vérifié). `ruff`, `ruff format --check`, `mypy` verts ; 313 tests réussis.
  `ruff --select BLE` ne signale plus que les 4 frontières voulues.

### 2026-09-27 — `data/` vérifié en CI

- **Fichiers** : `.github/workflows/ci.yml`, `CLAUDE.md`, `data/README.md`,
  `docs/pilotage/WIP/chantiers.md` ; suppression de `data/lab/` (2 notebooks).
- **Catégorie** : CI / filet de sécurité.
- **Fait** : nouveau job `python` (« Python (data) »), en parallèle de `typescript`.
  `astral-sh/setup-uv` épinglé par SHA (v10.2.0), uv 0.10.7 et Python 3.13 comme en
  local, cache sur `data/uv.lock`. `uv sync --locked --extra dev` échoue si `uv.lock` ne
  suit plus `pyproject.toml` ; puis `ruff check .`, `ruff format --check .`, `mypy`
  (strict, `src/ragcore`) et `pytest` (tests unitaires ; `integration` exclu par
  `addopts`). Aucun `.env.dev` ni aucune base n'est nécessaire.
- **Pourquoi** : rien ne vérifiait `data/`, alors que les chantiers 1 à 3 vont le
  refactorer. `ruff format --check .` échouait sur les notebooks de `data/lab/`,
  supprimés à cette occasion.
- **Vérification** : le job simulé sur un clone propre (sans `.venv`, `.env.dev` ni
  `conf/local`) : ruff 0 erreur, 189 fichiers formatés, mypy 0 erreur sur 127 fichiers,
  306 tests réussis (34 d'intégration désélectionnés), couverture 86 %.

### 2026-09-26 — `/completions` soumis au budget de stream par IP

- **Fichiers** : `backend/src/routes/chat.ts`, `backend/src/middleware/streamRateLimiter.ts`,
  `backend/src/__tests__/middleware/streamRateLimiter.test.ts`,
  `docs/technical/backend/ARCHITECTURE.md`, `CLAUDE.md`.
- **Catégorie** : sécurité / coût (limitation de débit).
- **Fait** : `POST /api/v1/chat/completions` passe par `streamRateLimiter`, comme
  `/streams`. Les trois transports du chat (SSE, JSON, WebSocket) tirent sur le même
  budget par IP (10/min par défaut). Un test vérifie qu'une fois le budget épuisé par
  `/streams`, `/completions` répond 429 `STREAM_RATE_LIMIT_EXCEEDED` ; il échoue sans le
  correctif (400).
- **Pourquoi** : `/completions` exécute tout le pipeline (TEI, Qdrant, Mongo, puis le LLM
  payant) mais n'était couvert que par le limiteur global (100 requêtes / 15 min, sans
  limite de rafale). Un client pouvait donc lancer 100 générations d'un coup, en plus de
  son budget de stream sur `/streams` et le WebSocket. Changement d'une ligne, sans effet
  sur le frontend, qui n'utilise que le WebSocket.
- **Vérification** : `npm run check` vert avant et après (backend : 17 suites, 115 puis
  116 tests).

## Pistes écartées

- **`readLines` (`infra/llm.ts`) perd une dernière ligne sans saut de ligne final** :
  comportement documenté ; le SSE termine chaque événement par une ligne vide, donc sans
  effet avec un fournisseur conforme.
