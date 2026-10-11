# Architecture — backend de serving

## Ce que c'est

Le moteur de recherche de Murphy : une API Express 5 / TypeScript qui, pour une
question, rend des documents juridiques classés et leurs passages correspondants
(ADR-028, ADR-030). Elle est **stateless par conception** : chaque requête recalcule
tout le pipeline, sans historique, sans session, sans cache et sans retry automatique
(fail-fast avec une erreur claire). Garder cela en tête avant d'ajouter cache, sessions
ou couches de retry.

Les bases sont supposées **pré-peuplées** par le pipeline d'ingestion (`data/`, hors de
cette stack) : les deux ne partagent que les bases.

## Les routes (ADR-030)

| Route | Rôle |
|---|---|
| `POST /api/v1/search`, corps `{ question, page? }` | Une page de la recherche : `{ page, pageCount, results }` |
| `GET /api/v1/documents/:identifier` | Le texte entier d'un document, chargé à la demande : `{ identifier, title, content }` |
| `GET /api/v1/health` (alias `/health/services`) | Sonde TEI, OpenSearch et Mongo |

La question passe dans le corps, jamais dans une URL : ni les logs d'accès ni un proxy
ne la gardent (ADR-010). Les logs n'en retiennent que la longueur.

Le contrat est `@murphy/contract/search` (`packages/contract/`, ADR-016) : les schémas
zod de la requête, de la réponse, du document et la liste des codes d'erreur. Les
réponses gardent l'enveloppe `{ status, data, meta }` de `buildApiResponse`.

## Le pipeline de recherche (`src/services/searchService.ts:searchDocuments`)

1. **Pagination** — `page` (1 par défaut) donne `from = (page - 1) × PAGINATION_SIZE`.
   `pageCount = ⌊PAGINATION_DEPTH / PAGINATION_SIZE⌋` (10 par défaut) : `from + size` ne
   dépasse jamais la profondeur. Une page au-delà est refusée
   (`PAGE_OUT_OF_RANGE`) avant tout appel ; une page en deçà mais au-delà des documents
   trouvés rend une liste vide.
2. **Embedding** (`ragService.embedQuestion`) → service TEI. La consigne
   `EMBEDDING_QUERY_INSTRUCTION` est collée devant la question, sans séparateur : le
   modèle attend `Instruct: {tâche}\nQuery:` devant une question, et rien devant les
   passages indexés (ADR-031).
3. **Recherche** (`ragService.retrieveDocuments`) → OpenSearch, requête hybride (voir
   « La recherche ») : `PAGINATION_SIZE` documents classés à partir de `from`, avec
   leurs passages correspondants.
4. **Lecture des documents** (`ragService.fetchDocuments`) → MongoDB `documents`, par
   `identifier`. Le titre en vient, et le texte de chaque passage est découpé dans le
   `content` de son document (`services/passages.ts`, voir « Le contrat avec
   l'ingestion »). Le `content` lui-même ne part pas au client.
5. **Réponse** — un résultat par document, dans l'ordre du classement : `identifier`,
   `title`, `documentType`, `nature`, et ses `passages` (`chunkId`, `text`, `start`,
   `end`). Aucun score ; les durées par étape sont journalisées (`Search completed`),
   pas renvoyées.

`GET /documents/:identifier` (`services/documentService.ts:readDocument`) lit un seul
document dans Mongo (`fetchDocument`) ; un identifiant inconnu donne
`DOCUMENT_NOT_FOUND`.

## Le contrat avec l'ingestion (ADR-015)

L'ingestion et le serving ne partagent aucun code : leur contrat est écrit dans l'ADR-015.
Ce que le backend lit :

| Où | Quoi |
|---|---|
| Index OpenSearch `OPENSEARCH_INDEX` | `_source` : `identifier`, `document_type` (l'un des quatre types), `nature` (facultatif) ; `chunk_id`, `char_start`, `char_end` des passages dans les `inner_hits` — validé à la lecture (`infra/searchHits.ts`) |
| Mongo `MURPHY_DATA.documents` | `identifier`, `title`, `content` — un document **entier** par `identifier` (`infra/mongodb.ts`) |

- **Offsets** : `char_start`/`char_end` comptent des **points de code** (le `str` Python).
  `services/passages.ts` les convertit une fois en unités UTF-16 : `start` / `end` d'un
  passage se lisent directement avec `content.slice(start, end)` sur le texte servi par
  `GET /documents`.
- **Violation** : un document OpenSearch sans champ du contrat, un document absent de
  Mongo ou des offsets hors de `content` lèvent une `RagError` `CONTRACT_VIOLATION`. Son
  message, logué, cite l'`identifier` ou le `chunk_id` ; le client reçoit un 500 : pas
  d'écart silencieux.

## La recherche (ADR-028, ADR-029)

**L'index** : son nom est `OPENSEARCH_INDEX`, la variable que l'ingestion lit dans le même
`.env.dev`. L'ingestion le crée et le remplit ; le backend ne fait que le lire. Au boot,
`OpenSearchClient.prepareSearch()` **refuse de démarrer** si OpenSearch est injoignable
ou si l'index n'existe pas, puis écrit le pipeline de recherche `murphy-rrf` (fusion RRF),
par une écriture idempotente.

**La requête** (`infra/hybridQuery.ts`) : une requête `hybrid` à quatre sous-requêtes
(lexicale, références, kNN sur les passages, kNN sur les titres), fusionnées par le
pipeline. Elle est décrite et mesurée dans
[`index-opensearch.md`](../data/reference/index-opensearch.md#la-requête) : les deux
doivent rester identiques. `k` et `pagination_depth` valent `PAGINATION_DEPTH`
(défaut 100) et restent les mêmes d'une page à l'autre, sinon le classement change.

**Les passages d'un document** (`services/passageRanking.ts`, ADR-028 §7, ADR-030 §3) :
- ceux de la sous-requête lexicale (ses `inner_hits`, 100 au plus) et les 3 plus proches
  de la sous-requête vectorielle, fusionnés par RRF sur leurs rangs (constante 60, celle
  d'OpenSearch) et dédoublonnés par `chunk_id` ;
- un document trouvé sans passage correspondant (par son titre, ses métadonnées, son texte
  parent) n'en a aucun : son texte se lit par `GET /documents`. Une section n'a jamais de
  passage.

## Erreurs (ADR-030 §4)

Une erreur est un **statut HTTP et un code** (`status.message`), jamais le message brut,
qui reste dans les logs. Chaque client traduit ses échecs par
`types/rag.ts:toRagError(failure, error)` en `RagError { stage, code }` ; l'étape
(`request`, `embedding`, `retrieval`) ne sert qu'aux logs. Le code vaut `TIMEOUT` quand
le **type** de l'erreur se termine par `TimeoutError` (`AbortSignal.timeout`, client
OpenSearch, `MongoNetworkTimeoutError`…), sinon celui du client.

`utils/errorResponse.ts:toErrorResponse` donne le statut, et `errorHandler` répond :

| Statut | Codes |
|---|---|
| 400 | `VALIDATION_ERROR`, `INVALID_JSON`, `PAGE_OUT_OF_RANGE` |
| 404 | `DOCUMENT_NOT_FOUND`, `NOT_FOUND` (route inconnue) |
| 413 | `PAYLOAD_TOO_LARGE` |
| 4xx | `INVALID_REQUEST_BODY`, toute autre erreur du parseur, à son statut |
| 429 | `SEARCH_RATE_LIMIT_EXCEEDED`, `RATE_LIMIT_EXCEEDED` |
| 502 | `EMBEDDING_FAILED`, `SEARCH_FAILED`, `DB_FETCH_FAILED` |
| 504 | `TIMEOUT` |
| 500 | `CONTRACT_VIOLATION`, `INTERNAL` (toute autre erreur) |

Un 4xx est journalisé en `warn`, le reste en `error`. Une recherche ne surveille pas le
départ du client : la réponse à un client parti est perdue, sans autre effet (ADR-030 §6).

## Clients d'infrastructure (`src/infra/`)

`EmbeddingClient` (TEI), `OpenSearchClient`, `MongoDbClient`. Chaque constructeur reçoit
sa section de `config` (`src/config.ts`) ; aucun ne lit l'environnement.

`infra/clients.ts:initInfraClients(config)` les crée **une fois au boot**, avant
l'écoute (`server.ts`) : connexion Mongo, vérification de l'index OpenSearch et écriture
du pipeline RRF (`prepareSearch`), puis le client TEI. Il peut refuser le démarrage.
Les requêtes y accèdent par `getInfraClients()`, qui lève s'il est appelé avant
l'initialisation ; `closeInfraClients()` ferme Mongo au shutdown gracieux. Ne jamais
`new`-er un client par requête.

Délais par défaut : TEI, Mongo et OpenSearch 10 s (`OPENSEARCH_TIMEOUT` vaut pour la
recherche comme pour le boot), sans relance.

## Conventions transverses

- **Réponses JSON** : `utils/response.ts:buildApiResponse(code, message, data?)` →
  `{ status: {code, message}, data?, meta: {timestamp, traceId} }` — pour toutes les
  réponses.
- **Validation** : `validation/searchRequest.ts:parseSearchRequest` applique le schéma du
  contrat ; un refus répond 400 `VALIDATION_ERROR` avec `errors: [{ field, message }]`.
  Les messages de zod ne citent pas la valeur reçue : la question n'en sort pas.
- **Logs** : Pino structuré (`utils/logger.ts`), un logger enfant par module
  (`rootLogger.child({ context: 'moduleName' })`).
- **Handlers async** enveloppés par `middleware/errorHandler.ts:asyncHandler` ;
  `notFoundHandler` et `errorHandler` enregistrés en dernier dans `app.ts`. Seul
  `express.json()` parse les corps (100 Kio au plus, `utils/requestLimits.ts`).
- **Ordre des middlewares** (`app.ts`) : requestLogger → helmet / rate-limit général /
  CORS (`middleware/security.ts`) → body parsing → routes → handlers d'erreur.
- **Quotas par IP** : le limiteur général (600 requêtes par 15 min, `RATE_LIMIT_*`) couvre
  toutes les routes ; `POST /search` ajoute `searchRateLimiter` (60 par minute,
  `SEARCH_RATE_LIMIT_*`), car chaque recherche appelle TEI et OpenSearch. `trust proxy`
  vaut `false` (`app.ts`) tant qu'aucun proxy n'est placé devant le backend.
- **Santé** : `/api/v1/health`, latence par service — `ok` / `degraded` (1 service down)
  / `down` (2+), 503 si non-ok.

## Dépendances externes

| Service | Rôle | Note |
|---|---|---|
| TEI (HuggingFace Text Embeddings Inference) | Embedding de la question | `POST /v1/embeddings`, GPU NVIDIA requis. Le modèle (`microsoft/harrier-oss-v1-0.6b`, 1024, Cosine) doit être celui de l'ingestion ; seule la question porte la consigne. |
| OpenSearch | Recherche hybride | Index `OPENSEARCH_INDEX`, vérifié au boot ; pipeline `murphy-rrf` écrit au boot. Sonde de santé : `/_cluster/health`. |
| MongoDB | Titre et texte des documents | Le texte des passages y est découpé ; `GET /documents` le sert entier. |
| Neo4j | — | Provisionné, **pas encore câblé** dans le chemin de requête (réservé : enrichissement graphe). |
