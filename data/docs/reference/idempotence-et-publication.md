# Idempotence, saga, publication

Comment le pipeline garantit qu'un document est écrit une fois et bien, qu'un run peut
être rejoué, et que le serving ne voit jamais un corpus incomplet.

## L'idempotence : le manifest décide

Le **manifest** (Mongo `LEGIFRANCE.manifest`, append-only) est le registre de toutes les
tentatives de traitement. Au parse (`computeIdempotence`), chaque document valide est
classé par `determine_operation` (`core/services/idempotence.py`) :

- identifiant **absent** du manifest → `INSERT` ;
- identifiant **présent** (dernière entrée par `processed_at`) → `UPDATE`.

Deux issues, pas trois : il n'y a **pas de SKIP**. Pas de hash de contenu — l'idempotence
se lit sur la présence de l'identifiant, jamais sur une comparaison d'octets. Un document
qui ne parse pas devient une entrée `EXCLUDED` (avec `source_path` et `reason`
obligatoires) : compté, jamais silencieusement ignoré.

Le modèle de rejeu est **at-least-once** : la source XML reste la vérité d'autorité, et
un document dont l'ingestion a échoué n'est pas inscrit au manifest — le run suivant le
re-traite naturellement.

## La saga (`application/saga.py`, `application/ingest_document.py`)

La phase 1 écrit chaque document par une saga de trois steps, **dans cet ordre** :

| # | Step | Forward | Compensation |
|---|---|---|---|
| 1 | `mongo_upsert` | `replace_one(upsert=True)` — remplacement atomique en place | `delete` (le rollback juste d'un INSERT) |
| 2 | `qdrant_upsert` | `delete_by_document` **puis** `upsert` des points | `delete_by_document` |
| 3 | `neo4j_merge_node` | `MERGE` du nœud (jamais ses arêtes) | conditionnelle : `DETACH DELETE` si orphelin, dé-hydratation en `:Pending` s'il est cité par d'autres |

En cas d'échec d'un step, les steps déjà exécutés sont compensés en ordre inverse, les
événements `saga.compensation.*` sont émis (y compris `saga.compensation.failed` si une
compensation rate — un écrit partiel doit être **compté**, pas seulement loggué), puis
l'exception d'origine est relevée : le document est perdu, **pas le run** (il est compté
`document.failed` et nommé dans `failures`).

Le **manifest n'est écrit qu'après le succès des trois steps** — c'est ce qui rend le
rejeu automatique : pas d'entrée, donc re-traitement au run suivant.

Choix d'ordre : Neo4j en dernier parce que c'est le store le moins librement compensable
(ses arêtes entrantes appartiennent à d'autres documents) — en position terminale, sa
compensation n'est appelée que si lui-même échoue.

### Les résiduels assumés (v0)

Deux fenêtres existent, toutes deux **hors du chemin `nuke_all`** (où le manifest est
vide, donc tout est INSERT) — elles ne concernent que le run incrémental, un chemin v1 :

- **compensation Mongo sur UPDATE** : elle supprime au lieu de restaurer l'ancien. Le
  vrai rollback versionné (snapshoter pour réinsérer) est un choix explicite de v1 ;
- **fenêtre intra-step Qdrant** : entre le delete et l'insert, les vecteurs du document
  sont absents. Qdrant n'offre pas de remplacement atomique par document — le
  delete-puis-insert est le modèle, pas un défaut (un simple upsert laisserait des points
  orphelins quand la nouvelle version a moins de chunks).

Dans les deux cas, l'at-least-once rattrape : le run suivant ré-écrit le document.

## Pourquoi les relations ont leur propre phase

La saga n'écrit qu'un **nœud**. Une arête (`MERGE (a) MATCH (b)`) exige que ses deux
extrémités existent : écrite au fil de l'ingestion, elle dépendrait de l'ordre de
traitement, et une cible pas encore écrite ferait tomber l'arête dans le vide — sans
erreur ni trace. D'où :

- la **barrière structurelle** du DAG (`ingestion_outcome` → `resolveRelations`) : la
  phase 2 ne démarre qu'après que tous les nœuds du run existent ;
- le **registre des pendantes** (`meta_pending_relations`) pour les cibles réellement
  absentes du corpus : une arête différée est une donnée, pas un vide. Ni TTL ni
  compteur d'essais — écrite une fois, **promue** une fois (quand sa cible arrive dans le
  delta d'un run : le rejeu est borné par `written_node_ids`, jamais par la taille du
  backlog), ou jamais (un lien légitime vers l'extérieur du corpus) ;
- chaque arête écrite est **taguée du `run_id`** : compensable à la maille du run sans
  emporter celles d'autres runs.

L'`owner_id` fait partie de la clé d'une pendante sans exception : « cette arête me
manque » est relatif au propriétaire du graphe — sans lui, promouvoir la pendante d'un
propriétaire effacerait celle d'un autre.

## `nuke_all` — le levier disque du développement

`maintenance.nuke_all: true` + `ENVIRONMENT=dev` (sinon levée avant toute écriture) :

- efface Mongo `LEGIFRANCE` (`documents` + `manifest`, puis **repose les index**),
  le graphe Neo4j entier, et **toutes** les collections Qdrant (y compris celles
  d'anciennes stratégies — c'est là que se cache la place perdue) ;
- **préserve `MURPHY_META`** : audit, bilans de run, pendantes, pointeur. Un nuke ne doit
  jamais rendre les runs passés invérifiables.

Après un nuke, le manifest est vide : tout redevient INSERT, et les résiduels de saga
ci-dessus n'existent pas.

## La publication : ce que le serving lira

Fin de run nominal (`after_pipeline_run`), dans l'ordre : troncatures déclarées → drain
de l'audit → **bilan persisté** (statut re-dérivé des compteurs) → **publication
conditionnelle** :

- bilan `ok` → le pointeur `MURPHY_META.meta_published_collection` (singleton, clé
  `current`) est remplacé : `collection_name` (l'empreinte de ce run), `run_id`,
  `document_count`, `published_at`. C'est **la** réponse à « quelle collection fait
  foi ? » — les noms de collections étant des empreintes, le serving ne peut pas
  deviner ;
- bilan `degraded` ou `failed` → le pointeur **ne bouge pas**. Le corpus de ce run est
  incomplet ; le serving continue de servir le dernier corpus complet, et l'utilisateur
  ne voit jamais la fuite.

Le pointeur publie aussi `serving_contract_version`, la version du contrat de payload
que ce code écrit (`SERVING_CONTRACT_VERSION`,
ADR-039 §3). D'où une
seconde condition, pour les seuls runs **restreints** (`--params source=…`, ou `SOURCE`
dans `.env.dev`) : ils ne réécrivent que leurs sources, donc ils ne publient que si le
pointeur en place porte **déjà** la même version (`may_publish`). Sinon la collection
mêlerait deux formats sous une version qui prétend le contraire. Un bump de version
impose donc un run complet : `kedro run --params source=all`.

Côté backend (`murphy-backend`, `src/infra/collectionPointer.ts`) : lecture du pointeur
au boot, repli **bruyant** sur `QDRANT_COLLECTION` si aucun run n'a jamais publié, et
dans tous les cas vérification que la collection existe réellement dans Qdrant (refus de
démarrer sinon — mieux vaut le découvrir au boot que sur la première question d'un
utilisateur).

C'est le point où l'équation de complétude (voir
[telemetrie.md](telemetrie.md#le-statut-dun-run)) cesse d'être un outil de diagnostic
pour devenir **la condition de publication**.
