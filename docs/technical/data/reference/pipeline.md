# Le déroulé d'un run, nœud par nœud

Référence exhaustive du pipeline d'ingestion. Le DAG vit dans
`src/ragcore/orchestration/kedro/pipeline.py`, les nœuds dans
`src/ragcore/orchestration/kedro/nodes/`, le câblage dans
`src/ragcore/orchestration/kedro/hooks.py`, qui délègue à `run_parameters.py` (lecture des
paramètres), `run_plan.py` (le plan du run), `stores.py` (clients et dépôts) et
`assembly.py` (embedder, briques, pool de la phase 1).

## Avant le premier nœud : `TelemetryHooks.before_pipeline_run`

Le hook est le **point d'assemblage** du run. Dans l'ordre :

1. **Chargement des settings** : `InfraSettings` + `EmbeddingRuntimeSettings`, lues du
   `.env.dev` **racine** (chemin absolu, jamais le CWD). Fichier absent = levée immédiate.
2. **Chargement de `parameters.yml`** (`run_parameters.load_parameters`) — sans fallback :
   un YAML illisible arrête le run (continuer avec les défauts baptiserait la collection
   Qdrant d'après une config que personne n'a choisie).
3. **Le plan du run** (`run_plan.plan_run`), une donnée figée dérivée une seule fois :
   - la `WorkflowConfig` (`run_parameters.build_workflow_config`), seule traduction
     YAML → objet du dépôt. C'est l'objet qui fait foi, pas le YAML ;
   - la collection Qdrant : `collection_name(workflow)` = le fingerprint blake2b de la
     config (32 hex). Jamais écrite à la main ;
   - les sources (`run_parameters.resolve_sources`) : `--params source=…` ou `SOURCE` du
     `.env`, défaut `all` = les six ingérables. Valeur inconnue = échec au démarrage en
     nommant les valides, **avant** qu'aucun client ni tracker ne soit ouvert ;
   - l'`owner_id` (`--params owner_id=…` prime sur `OWNER_ID`) ;
   - les arbitrages dev/prod : `run_parameters.resolve_embedding_enabled` (ADR-023 — le
     flag YAML n'a d'effet qu'en `dev`) et `run_parameters.resolve_node_hydration`
     (ADR-022 — nœuds Neo4j maigres hors `dev`).
4. **Ouverture du run de tracking** (`noop` par défaut, MLflow en option) — le run-id
   MLflow **est** le nom de collection : les deux sortent du même calcul et ne peuvent
   pas diverger.
5. **L'embedder** (`assembly.prepare_embedder`), une seule branche sur le provider :
   - `openai` : précondition TEI d'abord. `assert_service_serves_model` interroge
     `GET /info` du service et compare au modèle du workflow. TEI ignore le champ `model`
     des requêtes ; sans cette vérification, une divergence conteneur/YAML écrirait les
     vecteurs d'un modèle dans la collection nommée d'après un autre — en silence ;
   - `noop` : avertissement (vecteurs NULS écrits dans la collection du vrai modèle) ;
   - `local` : `LocalEmbedder`, qui charge le modèle au premier usage.
6. **Clients, index et dépôts du hook** (`stores.open_clients`, `ensure_indexes`,
   `open_document_stores`, `open_meta_stores`) : `ensure_data_indexes` (LEGIFRANCE) et
   `ensure_meta_indexes` (MURPHY_META).
7. **Le run démarre** : le `PipelineContext` (run_id uuid4-hex, owner_id, source —
   `None` si multi-source, started_at), la pile de télémétrie (registre construit depuis
   `EVENT_CATALOG`, backends JSONL `data/08_reporting/events/`, audit Mongo, agrégateur
   `RunStats`) et le `CollectionPublisher` qui publiera en fin de run.
8. **Briques de traitement** (`assembly.build_processing_stack`) : `CompositeConnector`
   (un connecteur par source, routé), `RoutingParser` (un `GenericParser` par source,
   chacun avec sa table de rôles), `StructuralChunker` (size/overlap du workflow),
   `RoutingRelationExtractor`, et l'embedder.
9. **Pool phase 1** (`assembly.build_runner`) : un `IngestionRunner` à 4 workers, armé de
   *fabriques* (runtime, télémétrie, use case) — jamais d'instances partagées.
10. **Service phase 2** : `ResolveRelationsService` (dépôts du hook, non parallélisé).
11. Tout est posé au catalogue (`catalog.save(...)`), l'événement `pipeline.run.started`
    est émis.

Pourquoi des fabriques : un client Motor/Neo4j/Qdrant est lié à la boucle asyncio qui le
touche en premier. Chaque worker construit donc **ses** clients sur **sa** boucle (le même
`stores.open_clients` que le hook : le code est partagé, pas les instances) ; ceux
du hook servent les nœuds non parallélisés (maintenance, phase 2).

## 1. `cleanup`

Entrées : `params:maintenance.cache_paths`. Supprime récursivement les fichiers sous les
chemins configurés (`data/cache`, `data/meta/events`). Émet
`maintenance.cleanup.executed`. Sortie : `cleanup_results` (compte + répertoires nettoyés).

## 2. `nukeAll`

Entrées : les quatre dépôts du hook, `params:maintenance`.

- `nuke_all: false` → ne supprime rien, mais fait quand même le **setup partagé** :
  `vector_repo.ensure_collection()`. La collection du fingerprint courant doit exister
  avant le pool — la laisser aux workers les mettrait en course (Qdrant répond 409 à tous
  sauf un).
- `nuke_all: true` → garde-fou d'abord : `ENVIRONMENT != "dev"` lève
  `NukeAllOutsideDevError` **avant de toucher la moindre base** (l'absence de la variable
  vaut `prod`). Puis efface :
  - Mongo `LEGIFRANCE` : collections `documents` + `manifest` (et **repose les index**,
    qu'un drop détruit avec la collection) ;
  - Neo4j : le graphe entier ;
  - Qdrant : **toutes** les collections du store (c'est là que dorment les collections
    d'anciennes stratégies) ;
  - **préservé** : la base méta `MURPHY_META` (audit, bilans, pendantes) — un nuke ne doit
    jamais emporter la mémoire de ce qu'on a fait.

Émet `maintenance.nuke_all.executed`. Sortie : `nuke_done` — consommé par `connect`
uniquement comme **signal d'ordre** (arête du DAG).

## 3. `connect`

Entrées : `connector`, le contexte, la télémétrie, le runtime du hook, `nuke_done`
(signal). Draine `connector.fetch_all()` → `list[RawDocument]`.

- Émet `document.fetched` **une fois**, avec `count` = le nombre de documents vus. Ce
  compte est le **dénominateur** de l'équation de complétude.
- Ce que le connecteur a écarté en amont (artefacts d'export, fichiers illisibles) est
  émis en `document.skipped`, une ligne par raison, **hors équation** : un fichier écarté
  n'est pas un document vu.

Sortie : `raw_documents`.

## 4. `computeIdempotence`

Entrées : `raw_documents`, `parser`, `manifest_repo`, contexte, télémétrie (de type
`WorkerTelemetry` : ce nœud *déclare* des inconnus), runtime, `params:exportation`.

Pour chaque `RawDocument` :

1. **Parse** (`parser.parse(raw)` → `ParseResult`). Deux familles d'échec, distinguées :
   - `ValidationError` (lisible mais irrecevable : ELI absent/mal formé) → événement
     `document.invalidated` (`reason=validation_error`) + entrée manifest `EXCLUDED`
     (identifier `None`, `source_path` + `reason` obligatoires) ;
   - toute autre exception (illisible) → idem avec `reason=parse_error`.
   Dans les deux cas le document part dans `to_skip`. Il n'y a **pas** de troisième voie :
   un document parse (INSERT/UPDATE) ou il est EXCLUDED — jamais ignoré.
2. **Signal des balises non-configurées** — TOUJOURS, avant le curseur :
   `record_unknown("tag.unconfigured", …)` et `record_unknown("root", …)` pour ce que la
   cascade du parser a rangé sans que la table le lui apprenne. C'est la vigie de dérive
   DILA : elle compte, que la donnée soit ensuite gardée ou retirée.
3. **Curseur `exportation.unconfigured`** (`ingest` | `skip`, validé — une coquille lève
   en nommant les valeurs valides) : en `skip`, les métadonnées non-configurées sont
   retirées du document juste avant l'ingestion. On compte d'abord, on filtre ensuite.
4. **Idempotence** : `manifest_repo.last_for_identifier(identifier, owner_id)` →
   `determine_operation` : identifiant inconnu du manifest = `INSERT`, connu = `UPDATE`.
   Pas de hash de contenu : la présence de l'identifiant décide, et elle seule.
5. Émet `document.parsed` (avec l'opération en payload).

La source de chaque événement/entrée manifest est `raw.source` (la vraie origine du
fichier), jamais `context.source` — qui vaut `None` en run multi-source.

Sorties : `to_process` (`list[(ParsedDocument, Operation)]`) et `to_skip` (`list[str]`).

## 5. `ingest` — la phase 1

Entrées : `to_process`, `runner`, contexte. Le nœud est mince : il lance
`IngestionRunner.run()` et rend son `IngestionOutcome`.

### Le pool (`application/ingestion_runner.py`)

- **Partition par clé document** : blake2b(identifiant) mod 4. Un identifiant donné n'est
  traité que par UN worker ; comme les `chunk_id` dérivent de l'identifiant parent, deux
  sagas ne peuvent pas se toucher — la garantie vient de la partition, pas d'un mutex.
  (Jamais `hash()` natif : randomisé par `PYTHONHASHSEED`, il rendrait la partition non
  reproductible.)
- **Un worker = une boucle + ses clients + sa télémétrie + son agrégat local.** Rien de
  partagé, donc rien à verrouiller. 4 workers (`_WORKER_COUNT`, assembly.py) — mesuré : en
  augmenter le nombre ne gagne rien, ~99,9 % du temps d'un document part dans l'embedding
  et le mur est le GPU (parse 0,9 ms, chunk 0,1 ms, embed ~1 364 ms).
- **Un échec de document ne casse pas le run** : l'exception est attrapée, comptée
  (`document.failed`, avec `reason` = le *type* de l'exception — le type regroupe, le
  message disperserait le breakdown) et le document rejoint `failures`
  (identifiant + message : un échec anonyme est un échec qu'on ne peut pas rejouer).
- **Fin de shard, ordre invariant** : `runtime.drain()` (attend les écritures d'audit en
  vol et compte celles qui ont levé) → `record_audit_failure` → `telemetry.close()` →
  `runtime.close()`.

### Le workload d'un document (`orchestration/kedro/workload.py`)

1. **Extraction** (`extractor.extract(parsed)`) — AVANT le chunking : elle sépare les
   cibles identifiées (→ relations, pour la phase 2) des cibles décrites (→ citations,
   champ du document, qui doit être posé avant l'écriture Mongo/Neo4j). Les inconnus
   d'extraction (`typelien`, `sens`, `identifiant`) sont déclarés à la télémétrie du
   worker.
2. **Chunking** (`chunker.chunk(parsed)`) — voir [sources.md](sources.md#le-chunking).
3. **Embedding** (`runtime.run(embedder.embed(chunks))`) — sauté si l'interrupteur
   d'embedding est coupé (dev, ADR-023) : zéro vecteur calculé ni écrit, Qdrant reste
   vide, Mongo/Neo4j normaux. Ce n'est **pas** `NoopEmbedder` (qui écrit N vecteurs nuls).
4. **Use case** (`IngestDocumentUseCase.execute`) — la saga d'écriture, voir
   [idempotence-et-publication.md](idempotence-et-publication.md#la-saga).
   Un use case **par worker**, mémorisé par identité de télémétrie (la fabrique crée
   trois clients ; l'appeler par document en créerait 1 121 jeux au lieu de 4).
5. Les relations extraites **ne sont pas écrites ici** : elles remontent dans
   `WorkloadResult.relations` vers la phase 2.

Sortie : `IngestionOutcome` — `stats` (réduction monoïde des N agrégats locaux),
`relations` (l'union), `written_node_ids` (le delta du run, qui borne le rejeu ciblé),
`failures`.

## 6. `resolveRelations` — la phase 2

Entrées : `ingestion_outcome` (LA barrière), `resolve_service`, runtime du hook, contexte.
Non parallélisé : un batch, sur la boucle du hook. Quatre temps
(`application/resolve_relations.py`) :

0. **Réduction transitive** (`reduce_transitively`, networkx) — à l'échelle du corpus, et
   ici seulement : la hiérarchie d'un article se déclare des deux côtés (sa fermeture
   d'ancêtres, et l'arbre des sections dans d'autres fichiers), donc réduire par document
   était impossible. Ne touche que la **contenance** (type `titre`) : réduire une
   citation détruirait un fait. Les arêtes réduites sont comptées à part
   (`reduced_count`) — redondantes, pas absentes.
1. **Écriture en batch** (`graph_repo.upsert_relations(relations, run_id)`). Chaque arête
   écrite est taguée du `run_id` : c'est ce qui la rend compensable à la maille du run
   sans emporter les arêtes d'autres runs. `relation.upserted` porte le compte des arêtes
   **réussies** (pas « tentées »).
2. **Les trous vont au cache** : chaque relation dont la cible manque devient une
   `PendingRelation` (`meta_pending_relations`, upsert-union sur la clé
   owner/source/target/type) + événement `relation.pending`. Une pendante peut rester
   pendante indéfiniment — un arrêt qui cite une directive jamais ingérée est un lien
   légitime vers l'extérieur, pas une erreur.
3. **Promotion ciblée** : on ne retente QUE les pendantes dont la cible figure dans
   `written_node_ids` (le delta de CE run) — le rejeu est borné par le delta, jamais par
   la taille du backlog. Les promues sont écrites, supprimées du cache et émises en
   `relation.promoted`.

Invariant de lisibilité : `written + pending == entrée réduite`.

Sortie : `ResolutionOutcome` (stats, written/pending/promoted/reduced counts).

## 7. `report` — le nœud terminal

Entrées : les deux outcomes, `to_skip`, `run_stats_sink` (le hook lui-même, vu comme un
protocole).

- **Pousse** `ingestion_outcome.stats` dans l'agrégat du run (`run_stats_sink.absorb`). C'est le seul point de
  remontée des stats des workers : Kedro **libère** un `MemoryDataset` dès son dernier
  lecteur, donc le hook ne pourrait pas le relire après le run — le DAG pousse, le hook ne
  tire pas. La phase 2 n'est PAS poussée : elle a tourné sur la télémétrie du hook, ses
  compteurs y sont déjà (les pousser les compterait deux fois).
- Compose le bilan : documents écrits/écartés/échoués (avec la liste nommée des
  `failures`), relations extraites/écrites/pendantes/réduites/promues, `unknowns`
  (vide = le vocabulaire de la source a tout couvert).

Limite assumée : si le pipeline casse **avant** ce nœud, les stats des workers ne
remontent pas — le run est `failed` (vrai), mais son bilan est pauvre.

## Après le dernier nœud : `after_pipeline_run` / `on_pipeline_error`

Chemin nominal (`after_pipeline_run`), dans l'ordre — et l'ordre est l'enjeu :

1. `pipeline.run.completed` émis.
2. **Déclaration des troncatures** : le compteur `truncations` de l'embedder (chunks
   raccourcis pour tenir dans la fenêtre du modèle) devient un événement
   `chunk.truncated`. Le corpus est complet, mais la config est à corriger.
3. **Drain avant bilan** : les écritures d'audit encore en vol sont attendues ; celles qui
   ont échoué entrent dans l'agrégat (`audit.write.failed`). Un bilan persisté avant de le
   savoir déclarerait `ok` un run dont il ne peut plus prouver la complétude.
4. **Persistance du bilan** (`_persist_run_summary("ok")`) : le statut annoncé est
   **re-dérivé des compteurs** (`RunSummary.of` → `_status_from`) — voir
   [telemetrie.md](telemetrie.md#le-statut-dun-run). Écrit en JSON
   (`data/08_reporting/stats/`) et upsert Mongo (`meta_run_summaries`).
5. **Publication** (`application/publish_collection.py:CollectionPublisher`) : si et seulement si le bilan dit `ok`, le
   pointeur `meta_published_collection` est mis à jour avec l'empreinte de ce run. Un run
   `degraded` ne publie pas — le serving reste sur le dernier corpus complet.
6. **Tracking** : le bilan part au tracker (MLflow le cas échéant), et le run d'expérience
   est fermé — `end_run` en `finally`, pour qu'un backend injoignable ne laisse pas un run
   MLflow ouvert que le lancement suivant polluerait.
7. `runtime.close()`.

Chemin d'erreur (`on_pipeline_error`) : `pipeline.run.failed` émis, puis les **mêmes
étapes 2-3** (les troncatures et le drain valent aussi sur un run cassé), bilan persisté
en `failed` (avec le message d'erreur), tracking fermé, runtime fermé.
