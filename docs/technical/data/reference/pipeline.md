# Le déroulé d'un run, nœud par nœud

Référence exhaustive du pipeline d'ingestion. Le DAG vit dans
`src/ragcore/orchestration/kedro/pipeline.py`, les nœuds dans
`src/ragcore/orchestration/kedro/nodes/`, le câblage dans
`src/ragcore/orchestration/kedro/hooks.py`, qui délègue à `parameters_model.py` (la forme
de `parameters.yml`), `run_parameters.py` (lecture et arbitrages), `run_plan.py` (le plan du run), `stores.py` (clients et dépôts) et
`assembly.py` (embedder, briques, pool de la phase 1) et `run_session.py` (l'état du
run et sa clôture).

## Avant le premier nœud : `TelemetryHooks.before_pipeline_run`

Le hook est le **point d'assemblage** du run. Dans l'ordre :

1. **Chargement des settings** : `InfraSettings`, `EmbeddingRuntimeSettings` et
   `ChunkingSettings`, lues du
   `.env.dev` **racine** (chemin absolu, jamais le CWD). Fichier absent = levée immédiate.
2. **Chargement de `parameters.yml`** (`run_parameters.load_parameters`) — sans fallback :
   un YAML illisible arrête le run.
3. **Le plan du run** (`run_plan.plan_run`), une donnée figée dérivée une seule fois :
   - la validation du fichier entier (`parameters_model.validate_parameters`), `--params`
     compris : un modèle strict, sans défaut dans le code. Clé inconnue, absente ou mal
     typée = échec au démarrage, toutes les erreurs listées ensemble ;
   - la découpe : `CHUNKING_MAX_CHARS` et `CHUNKING_OVERLAP_CHARS` (`ChunkingSettings`) ;
   - l'index OpenSearch : `OPENSEARCH_INDEX`, un nom fixe lu des settings ;
   - les sources (`run_parameters.resolve_sources`) : `--params source=…` ou `SOURCE` du
     `.env`, défaut `all` = les six ingérables. Valeur inconnue = échec au démarrage en
     nommant les valides, **avant** qu'aucun client ne soit ouvert ;
   - l'arbitrage dev/prod : `run_parameters.resolve_dev_settings` applique `parameters.yml`
     tel quel en `dev`, et le remplace ailleurs par les valeurs sûres (`nuke_all` coupé,
     embedding calculé, métadonnées non configurées retirées, nœuds Neo4j maigres), avec
     un avertissement au log ;
4. **L'embedder** (`assembly.prepare_embedder`) : TEI, seul embedder. Précondition
   d'abord : `served_model.inspect_served_model` interroge `GET /info` et compare le
   modèle servi à `EMBEDDING_MODEL`. TEI ignore le champ `model` des requêtes ; sans
   cette vérification, un conteneur pas redémarré après un changement de modèle écrirait
   les vecteurs d'un autre modèle que celui que le backend interroge — en silence. Puis
   une requête de sonde mesure la dimension des vecteurs, transmise à l'index du run.
   Échec = run arrêté avant tout nœud ;
5. **Clients, index et dépôts du hook** (`stores.open_clients`, `ensure_indexes`,
   `open_document_stores`, `open_meta_stores`) : `ensure_data_indexes` (MURPHY_DATA :
   documents, pendantes), `ensure_meta_indexes` (MURPHY_META : bilans, statistiques) et
   `ensure_graph_constraints` (Neo4j : unicité de `(:Document).identifier`).
6. **La session du run** (`run_session.RunSession`) : le `PipelineContext` (run_id
   uuid4-hex, `sources` résolues par le plan, started_at ; sa propriété `source` vaut la
   source unique, ou `None` si multi-source), la pile de
   télémétrie (`WorkerTelemetryStack` : backends console, agrégateur `RunStats` et
   agrégateur de mesures) et les `RunAggregates` du run (compteurs, mesures, horloge
   des étapes), posés au catalogue sous `run_sink` et `stage_clock`.
7. **Briques de traitement** (`assembly.build_processing_stack`) : `CompositeConnector`
   (un connecteur par source, routé), `RoutingParser` (un `GenericParser` par source,
   chacun avec sa table de rôles), `StructuralChunker` (`CHUNKING_MAX_CHARS` / `CHUNKING_OVERLAP_CHARS`),
   `RoutingRelationExtractor`, et l'embedder.
8. **Pool phase 1** (`assembly.build_runner`) : un `IngestionRunner` à 4 workers, armé de
   *fabriques* (runtime, télémétrie, use case) — jamais d'instances partagées.
9. **Service phase 2** : `ResolveRelationsService` (dépôts du hook, non parallélisé).
10. Tout est posé au catalogue (`catalog.save(...)`).

Pourquoi des fabriques : un client Motor/Neo4j/OpenSearch est lié à la boucle asyncio qui le
touche en premier. Chaque worker construit donc **ses** clients sur **sa** boucle (le même
`stores.open_clients` que le hook : le code est partagé, pas les instances) ; ceux
du hook servent les nœuds non parallélisés (maintenance, phase 2). Chacun inscrit la
fermeture de ses clients auprès de son runtime (`AsyncRuntime.defer_close`), qui
l'exécute dans la boucle juste avant de la fermer.

## 1. `nukeAll`

Entrées : les dépôts Mongo et Neo4j du hook, l'index OpenSearch, `transit_repo`,
`nuke_all` (du plan du run), le runtime du hook.

- **Toujours** : vide `MURPHY_DATA.transit_relations`, avant la phase 1 (ADR-034 §4).

- `nuke_all: false` → ne supprime rien, mais fait quand même le **setup partagé** :
  `search_index.ensure_index()`, qui crée l'index s'il est absent, avec ses analyseurs et
  son mapping ([index-opensearch.md](index-opensearch.md)) et la dimension mesurée. Un
  index existant d'une autre dimension arrête le run : il n'est jamais modifié, et un
  modèle d'une autre dimension ferait rejeter chaque document. L'index du run doit exister
  avant le pool — la laisser aux workers les mettrait en course (OpenSearch refuse toutes
  les créations sauf une).
- `nuke_all: true` → le garde-fou a déjà joué en amont : hors `ENVIRONMENT=dev`, `plan_run`
  ignore `parameters.yml` et `nuke_all` arrive ici à `false` (l'absence de la variable vaut
  `prod`). Le nœud n'efface donc qu'en dev :
  - Mongo `MURPHY_DATA` : les collections `documents`, `pending_relations`,
    `unformatted_relations` et `transit_relations`
    (`schemas.reset_data_collections`, qui **repose les index** qu'un drop détruit avec
    la collection) ;
  - Neo4j : le graphe entier ;
  - OpenSearch : **seulement** l'index du run, recréé aussitôt par `ensure_index()`. Les
    index système (Dashboards, plugins) vivent dans le même cluster ;
  - **préservé** : la base méta `MURPHY_META` (bilans et statistiques de run) — un nuke ne doit
    jamais emporter la mémoire de ce qu'on a fait.

Chaque effacement est annoncé en `logger.warning`. Sortie : `nuke_done` — consommé par `ingest`
uniquement comme **signal d'ordre** (arête du DAG).

## 2. `ingest` — la phase 1, en flux

Entrées : `connector`, `parser`, `runner`, l'index OpenSearch, le contexte, la télémétrie
du hook, son runtime, `skip_unconfigured` (du plan du run), `run_sink`, `stage_clock`,
`nuke_done` (signal). Sorties : `ingestion_outcome` et `to_skip`.

La lecture, le parse et l'ingestion s'enchaînent dans un seul nœud (ADR-034 §2) : aucune
étape ne matérialise le corpus. `ragcore` expose chaque étape comme une fonction sur un
itérateur, testée seule (`application/source_reading.py`,
`application/document_parsing.py`, `application/ingestion_runner.py`) ; le nœud les
compose. Kedro ne voit qu'un nœud : les logs de progression et `statistics` disent où
passe le temps.

### La lecture (`SourceReading`)

1. **Passe 1** (`connector.discover()`, `stages_s.discovery`) : chaque connecteur indexe
   son arborescence sans ouvrir un fichier, et garde les clés que retient
   `ingestion_ratio` ([configuration.md](configuration.md)). L'inventaire de chaque
   source (documents retenus sur le total) rejoint le bilan (`run_sink`) et part au
   log, en avertissement pour un run partiel. Le total retenu sert à la progression.
2. **Passe 2** (`connector.fetch_all()`) : un document à la fois. Chacun est mesuré
   (`xml_bytes`, `facets`, et `step_ms.read`, le temps écoulé depuis le document
   précédent).
3. **En fin de flux**, même quand le run casse : `document.fetched` **une fois**, avec
   `count` = le nombre de documents vus — le **dénominateur** de l'équation de
   complétude ; puis un compteur par raison pour ce que le connecteur a écarté,
   `document.version_skipped` (artefacts d'export), `document.unreadable` (fichiers
   illisibles) et `document.id_mismatch` (`<ID>` différent du nom de fichier), **hors
   équation** : un fichier écarté n'est pas un document vu.

### Le parse (`DocumentParsing`)

Pour chaque `RawDocument` :

1. **Parse** (`parser.parse(raw)` → `ParseResult`). Deux familles d'échec, distinguées :
   - `ValidationError` (lisible mais irrecevable : identifiant absent/mal formé) → événement
     `document.invalidated` (`reason=validation_error`, `uid` = chemin source, `error`) ;
   - `ParseError` (illisible) → idem avec `reason=parse_error`.
   Dans les deux cas le document part dans `to_skip`. Toute autre exception sort du
   contrat du parser : c'est un bug du run, elle remonte et l'arrête. Il n'y a **pas** de
   troisième voie : un document parse ou il est rejeté — jamais ignoré.
2. **Signal des données non-configurées** — TOUJOURS, avant le curseur :
   `record_unknown` en `tags`, `links` et `roots` (clés chemin-complet, ADR-024) pour ce
   que la cascade du parser a rangé sans que la table le lui apprenne. C'est la vigie de dérive
   DILA : elle compte, que la donnée soit ensuite gardée ou retirée.
3. **Curseur `skip_unconfigured`** (booléen, arbitré par `plan_run` en tête de
   run, avant tout nœud) : à `true`, les métadonnées non-configurées sont
   retirées du document juste avant l'ingestion (les arêtes non configurées le sont à
   l'extraction). Hors `ENVIRONMENT=dev`, le plan impose `true`. On compte d'abord, on
   filtre ensuite.
4. Émet `document.parsed`. Le document part à l'ingestion, qu'il soit déjà en base ou
   non : la saga le réécrit en place (voir [idempotence.md](idempotence.md)).

La source de chaque événement est `raw.source` (la vraie origine du
fichier), jamais `context.source` — qui vaut `None` en run multi-source. La durée de
chaque parse est mesurée (`step_ms.parse`), document rejeté compris.

Les rejetés forment `to_skip`.

### La file et le pool (`application/ingestion_runner.py`, `document_queue.py`)

La lecture et le parse tournent dans le thread du nœud ; ils déposent chaque document
dans une **file bornée**, que le premier worker libre consomme (ADR-034 §3). Autour, le
nœud suspend le rafraîchissement de l'index (`refresh_interval: -1`), puis, dans un
`finally`, lance un `_refresh` et rend au réglage sa valeur par défaut : même un run en
échec laisse un index cherchable. Pendant le run, le backend ne voit donc pas les
documents réécrits. Un run arrivé au bout fusionne ensuite l'index en un seul segment
(`_forcemerge`), puis le rafraîchit : chaque requête kNN ne parcourt plus qu'un graphe
HNSW (voir [index-opensearch.md](index-opensearch.md#lécriture)). Un run en échec ne
fusionne pas. Lecture, parse et pool forment `stages_s.phase1`.

- **Capacité : le nombre de workers.** Un double tampon : chaque worker trouve un
  document prêt en finissant le sien. Au pire 2n + 1 documents vivent à la fois (n
  traités, n en file, un en parse).
- **Un identifiant n'est traité que par UN worker** : la clé est unique par source, et
  les préfixes d'identifiants ne se croisent pas entre sources. Comme les `chunk_id`
  dérivent de l'identifiant parent, deux sagas ne peuvent pas se toucher — la garantie
  vient du flux, pas d'un mutex.
- **Un worker = un thread + une boucle + ses clients + sa télémétrie + ses agrégats
  locaux.** Seuls la file, la progression (sous un verrou) et ce que les workers
  déposent en sortant sont partagés. 4 workers (`_WORKER_COUNT`, assembly.py) — mesuré
  sur l'extrait : en augmenter le nombre ne gagnait rien, l'embedding prenait ~99,9 % du
  temps d'un document. Une ligne de progression (documents traités, total, débit) part
  au log toutes les 30 s au plus (`application/progress.py`).
- **Les attentes sont mesurées** (`queues`) : `producer_blocked_s`, l'attente de la
  lecture devant une file pleine (souvent bloquée, elle désigne les workers), et
  `worker_idle_s`, celle d'un worker devant une file vide (souvent inactifs, ils
  désignent la lecture).
- **Un échec de document ne casse pas le run** : l'exception est attrapée, comptée
  (`document.failed`, avec `reason` = le *type* de l'exception — le type regroupe, le
  message, gardé dans `error`, disperserait les raisons), journalisée en `logger.error`
  (seule trace de *quel* document a échoué) et le document rejoint `failures`
  (identifiant + message : un échec anonyme est un échec qu'on ne peut pas rejouer).
- **Arrêt** : en fin de flux, la lecture dépose un marqueur de fin par worker, y compris
  quand elle échoue ; les workers vident la file puis s'arrêtent. Un worker qui tombe
  hors d'un document arrête la file : la lecture cesse d'attendre une place, les autres
  workers s'arrêtent, et l'erreur est relevée dans le thread du nœud.
- **Fin d'un worker** : il dépose ses agrégats (compteurs, mesures) et son résultat,
  même en échec, puis `telemetry.close()` → `runtime.close()`, qui ferme d'abord ses
  clients. Le runner remet les agrégats à `run_sink` **même quand le pool lève** : un
  run qui casse plus loin garde dans son bilan et ses statistiques ce que la phase 1 a
  fait.

### Le workload d'un document (`orchestration/kedro/workload.py`)

1. **Extraction** (`extractor.extract(parsed)`) — AVANT le chunking : elle sépare les
   cibles identifiées (→ relations, pour la phase 2) des cibles décrites (→ relations
   non formatées, que la saga du document écrit, ADR-021). Les `typelien` non traduits
   sont déclarés à la télémétrie du worker (`links`), les liens qu'on ne sait pas écrire
   comptés (`relation.unknown`). Avec `skip_unconfigured`, les arêtes d'un type non
   configuré sont retirées (ADR-024).
2. **Chunking** (`chunker.chunk(parsed)`) — voir [sources.md](sources.md#le-chunking).
3. **Embedding** (`embedder.embed(chunks)`) — un document sans chunk (une section, un
   texte au `content` vide) embarque son titre à la place (`embedder.embed_text`,
   `title_embedding`, ADR-029). Sauté si l'interrupteur d'embedding est coupé (dev,
   ADR-012) : zéro vecteur calculé, les passages partent dans l'index sans vecteur,
   cherchables par leur seul texte. Le résultat est un `SearchContent`.
4. **Use case** (`IngestDocumentUseCase.execute`) — la saga d'écriture, voir
   [idempotence.md](idempotence.md#la-saga).
   Un use case **par worker**, mémorisé par identité de télémétrie (la fabrique crée
   trois clients ; l'appeler par document en créerait 1 121 jeux au lieu de 4).
5. Les relations extraites **ne deviennent pas des arêtes ici** : la saga les écrit dans
   `MURPHY_DATA.transit_relations`, que la phase 2 consomme (ADR-034 §4). Rien ne
   remonte du workload.
6. **Mesures** : `content_chars`, `chunks`, `relations`, et la durée de l'embedding et
   de l'écriture dans chaque base (`step_ms.embed|mongo|opensearch|neo4j`, rendues par
   la saga).

Sortie : `IngestionOutcome` — `stats` (réduction monoïde des N agrégats locaux, déjà
remise à `run_sink`), `written_node_ids` (le delta du run, qui borne le rejeu ciblé),
`failures`.

## 3. `resolveRelations` — la phase 2

Entrées : `ingestion_outcome` (LA barrière), `resolve_service`, runtime du hook, contexte,
`stage_clock`. Non parallélisé, sur la boucle du hook (`application/resolve_relations.py`,
`application/relation_writer.py`). Les relations sont lues dans `transit_relations`, pour
ce run, et la mémoire est bornée par la plus grande composante connexe (ADR-034 §5).

1. **Les composantes** (`find_components`, `stages_s.components`) — la **réduction
   transitive** ne touche que la **contenance** (`REDUCIBLE_TYPES`) : réduire une
   citation détruirait un fait. Elle se fait ici, à l'échelle du corpus : la hiérarchie
   d'un article se déclare des deux côtés (sa fermeture d'ancêtres, et l'arbre des
   sections dans d'autres fichiers), donc réduire par document était impossible. Deux
   composantes connexes n'ont aucun chemin commun : réduire composante par composante
   donne la réduction du graphe entier. Les couples (source, cible) `contient` sont lus
   en flux, et un union-find (`core/services/connected_components.py`) en tire les
   composantes : une entrée par nœud, et leur taille (nœuds, relations), jamais les
   arêtes. Chaque composante est mesurée (`components.nodes`, `components.relations`).
2. **La réduction** (`stages_s.phase2_write`, comme la suite) — les composantes sont
   lues par groupes (`_COMPONENT_READ_BUDGET`, 10 000 nœuds : les petites partagent un
   aller-retour, une grande le prend seule ; le `$in` est découpé par le dépôt), puis
   **chacune réduite seule** par `reduce_transitively` (networkx). **Aucun plafond** :
   couper une composante rendrait la réduction approximative. Un cycle rend la réduction
   indéfinie : sa composante est gardée telle quelle, et elle seule. Les arêtes réduites
   sont comptées à part (`reduced_count`) — redondantes, pas absentes.
3. **Les autres verbes** traversent sans réduction, par lots de 5 000 lignes, paginés
   sur `_id`.
4. **Écriture par lots** (`RelationWriter`, `graph_repo.upsert_relations`) : les arêtes
   conservées vont dans un tampon de 5 000, qui peut mêler plusieurs composantes et
   plusieurs verbes. Neo4j les reçoit en requêtes `UNWIND` de 5 000 arêtes d'un même
   verbe (`_RELATION_BATCH_SIZE`), jamais une par arête. Un `MATCH` sans résultat retire
   la ligne du lot sans erreur : seuls les indices rendus distinguent l'arête écrite de
   la différée. Chaque arête écrite est taguée du `run_id` : c'est ce qui la rend
   compensable à la maille du run sans emporter les arêtes d'autres runs.
   `relation.upserted` porte le compte des arêtes **réussies** (pas « tentées »).
5. **Les trous vont au cache** : chaque relation dont la cible manque devient une
   `PendingRelation` (`MURPHY_DATA.pending_relations`, upsert-union sur la clé
   source/target/type) + événement `relation.pending`. Une pendante peut rester
   pendante indéfiniment — un arrêt qui cite une directive jamais ingérée est un lien
   légitime vers l'extérieur, pas une erreur.
6. **Suppression au fil de l'eau** : les lignes de transit d'un groupe de composantes ou
   d'un lot ne sont supprimées qu'une fois le tampon qui porte leurs arêtes vidé —
   écrites, en attente ou réduites. Si la collection n'est pas vide en fin de phase, le
   run échoue (`TransitNotDrainedError`, ADR-034 §6) : c'est un bug, pas un état
   dégradé.
7. **Promotion ciblée** : on ne retente QUE les pendantes dont la cible figure dans
   `written_node_ids` (le delta de CE run) — le rejeu est borné par le delta, jamais par
   la taille du backlog. `written_node_ids` reste en mémoire (~2,1 M identifiants,
   ~200 Mo pour LEGI) ; seuls le `$in` qui le porte et la suppression des promues sont
   découpés, par tranches de 10 000 (`_QUERY_CHUNK`) : une requête Mongo ne dépasse pas
   16 Mo (ADR-034 §7). Les promues sont écrites, supprimées du cache et émises en
   `relation.promoted`.

Invariant : `written + pending + reduced == extracted`, les lignes lues en transit.

Sortie : `ResolutionOutcome` (extracted/written/pending/reduced/promoted counts).

## 4. `report` — le nœud terminal

Entrées : les deux outcomes, `to_skip`. Sans I/O.

Compose le bilan : documents écrits/écartés/échoués (avec la liste nommée des
`failures`), relations extraites/écrites/pendantes/réduites/promues, `unknowns` (vide =
le vocabulaire de la source a tout couvert). Il ne pousse rien : `ingest` a déjà remis les
agrégats des workers, et la phase 2 a émis sur la télémétrie du hook.

## Après le dernier nœud : `after_pipeline_run` / `on_pipeline_error`

Les deux chemins passent par `RunSession.close(status)` (`run_session.py`). Chemin
nominal (`after_pipeline_run`), dans l'ordre — et l'ordre est l'enjeu :

1. **Déclaration des troncatures** : le compteur `truncations` de l'embedder (chunks
   raccourcis pour tenir dans la fenêtre du modèle) devient un événement
   `chunk.truncated`. Le corpus est complet, mais la config est à corriger.
2. **Persistance du bilan** (statut demandé : `ok`) : le statut annoncé est
   **re-dérivé des compteurs** (`RunSummary.of` → `_status_from`) — voir
   [telemetrie.md](telemetrie.md#le-statut-dun-run). Upsert Mongo
   (`run_summaries`).
3. **Persistance des statistiques** (`statistics`) : la durée des étapes et les mesures
   réduites, voir [telemetrie.md](telemetrie.md#les-statistiques-dun-run).
4. Le hook ferme son runtime.

Chemin d'erreur (`on_pipeline_error`) : la **même clôture** (les troncatures valent aussi
sur un run cassé), bilan persisté en `failed` (avec le message d'erreur), statistiques
persistées, runtime fermé.
Si l'assemblage a échoué avant que la session existe, le hook ne fait que fermer son
runtime.
