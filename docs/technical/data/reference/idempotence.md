# Idempotence et saga

Comment le pipeline garantit qu'un document est écrit une fois et bien, et qu'un run peut
être rejoué.

## L'idempotence : réécrire en place

Pas de registre ni de comparaison : chaque run relit toute la source, et chaque document
qui parse (`parseDocuments`) est réécrit sous son `identifier`, qu'il soit déjà en base ou
non. Les trois écritures de la saga sont idempotentes (`replace_one` Mongo, `PUT` du
document OpenSearch, `MERGE` Neo4j) : rejouer un run donne le même état. Il n'y a
**pas de SKIP** ni de hash de contenu.

Un document qui ne parse pas émet `document.invalidated` (`reason`, chemin source,
message d'erreur), journalisé en console et compté au bilan : jamais silencieusement
ignoré.

Le modèle de rejeu est **at-least-once** : la source XML reste la vérité d'autorité, et
un document dont l'ingestion a échoué est réécrit au run suivant.

Le manifest (`manifest`, dans la base de données alors nommée `LEGIFRANCE`) qui classait
les documents en INSERT/UPDATE a été retiré : le classement ne changeait aucune écriture
(ADR-020).

## La saga (`application/saga.py`, `application/ingest_document.py`)

La phase 1 écrit chaque document par une saga de quatre steps, **dans cet ordre** :

| # | Step | Forward | Compensation |
|---|---|---|---|
| 1 | `mongo_upsert` | `replace_one(upsert=True)` — remplacement atomique en place | `delete` (le rollback juste d'une première écriture) |
| 2 | `mongo_unformatted_upsert` | upsert-union des relations non formatées du document (ADR-021) | `delete_first_seen` : seules les lignes du document nées dans ce run |
| 3 | `opensearch_index` | `PUT /<index>/_doc/<identifier>` : le document entier, passages compris, remplacé d'un coup | `delete_document` par `_id` (un document absent n'est pas une erreur) |
| 4 | `neo4j_merge_node` | `MERGE` du nœud (jamais ses arêtes) | aucune : step terminal, jamais compensé ; un `MERGE` raté est annulé par sa transaction |

En cas d'échec d'un step, les steps déjà exécutés sont compensés en ordre inverse, les
événements `saga.compensation.*` sont émis (y compris `saga.compensation.failed` si une
compensation rate — un écrit partiel doit être **compté**, pas seulement loggué), puis
l'exception d'origine est relevée : le document est perdu, **pas le run** (il est compté
`document.failed` et nommé dans `failures`).

`document.persisted` **n'est émis qu'après le succès des quatre steps** : un document à
moitié écrit n'est jamais compté ingéré.

Choix d'ordre : Neo4j en dernier parce que c'est le store le moins librement compensable
(ses arêtes entrantes appartiennent à d'autres documents). En position terminale, il n'a
jamais à l'être : seuls les steps terminés sont compensés.

Le step OpenSearch écrit un document par requête, et non par `_bulk` comme le prévoyait
l'ADR-028 : la saga traite un document à la fois, et un `_bulk` d'une seule opération
n'apporterait rien. Grouper les documents sortirait l'écriture de leur saga, sans
compensation possible pour un lot à moitié rejeté ; le coût d'une requête par document
est négligeable devant l'embedding. Un document rejeté par le mapping (une date mal
formée, un champ inconnu) fait échouer le step, et la saga compense.

### Les résiduels assumés (v0)

Deux fenêtres existent, toutes **hors du chemin `nuke_all`** (où les bases sont
vides, donc rien n'est réécrit) — elles ne concernent que le run incrémental, un chemin
v1 :

- **compensation Mongo ou OpenSearch d'une réécriture** : elle supprime au lieu de
  restaurer l'ancien. Le vrai rollback versionné (snapshoter pour réinsérer) est un choix
  explicite de v1 ;
- **compensation des relations non formatées déjà connues** : elles s'accumulent, et la
  compensation ne retire que celles nées dans le run ; une relation déjà en base garde
  son `last_seen_run` avancé par le run qui a échoué.

Dans les deux cas, l'at-least-once rattrape : le run suivant ré-écrit le document.

## Pourquoi les relations ont leur propre phase

La saga n'écrit qu'un **nœud**. Une arête (`MERGE (a) MATCH (b)`) exige que ses deux
extrémités existent : écrite au fil de l'ingestion, elle dépendrait de l'ordre de
traitement, et une cible pas encore écrite ferait tomber l'arête dans le vide — sans
erreur ni trace. D'où :

- la **barrière structurelle** du DAG (`ingestion_outcome` → `resolveRelations`) : la
  phase 2 ne démarre qu'après que tous les nœuds du run existent ;
- le **registre des pendantes** (`MURPHY_DATA.pending_relations`) pour les cibles réellement
  absentes du corpus : une arête différée est une donnée, pas un vide. Ni TTL ni
  compteur d'essais — écrite une fois, **promue** une fois (quand sa cible arrive dans le
  delta d'un run : le rejeu est borné par `written_node_ids`, jamais par la taille du
  backlog), ou jamais (un lien légitime vers l'extérieur du corpus) ;
- chaque arête écrite est **taguée du `run_id`** : compensable à la maille du run sans
  emporter celles d'autres runs.

## `nuke_all` — le levier disque du développement

`nuke_all: true` + `ENVIRONMENT=dev` (ailleurs, `parameters.yml` est ignoré : rien n'est effacé) :

- efface Mongo `MURPHY_DATA` (`documents`, `pending_relations` et
  `unformatted_relations`, puis **repose les index**), le graphe Neo4j entier, et l'index
  OpenSearch du run (`OPENSEARCH_INDEX`), recréé aussitôt ; les index système du cluster
  restent. Les pendantes partent avec le corpus : elles pointent vers des
  nœuds effacés, et le run suivant retrouve celles qui manquent toujours ;
- **préserve `MURPHY_META`** : les bilans de run. Un nuke ne doit jamais rendre les
  runs passés invérifiables.

Après un nuke, les bases sont vides : tout est première écriture, et les résiduels de
saga ci-dessus n'existent pas.

## Ce que le serving lit

Il n'y a pas d'étape de publication : le backend interroge l'index `OPENSEARCH_INDEX`,
que le run réécrit en place (ADR-018, ADR-028). Seul le rafraîchissement est différé :
suspendu pendant la phase 1, il est relancé à sa fin, même en échec. Un run `degraded` ou
`failed` laisse donc un corpus incomplet **dans l'index servi** : lire le bilan (voir
[telemetrie.md](telemetrie.md#le-statut-dun-run)) et relancer le run.
