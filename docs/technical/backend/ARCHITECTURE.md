# Architecture — backend de serving

## Ce que c'est

Le moteur de recherche de Murphy : une API Express 5 / TypeScript qui, pour une
question, rend des documents juridiques classés et leurs passages correspondants
(ADR-028, ADR-030). Elle fait aussi expliquer par un LLM les documents que
l'utilisateur a choisis, et eux seuls (ADR-033). Elle est **stateless par conception** : chaque requête recalcule
tout le pipeline, sans historique, sans session, sans cache et sans retry automatique
(fail-fast avec une erreur claire). Garder cela en tête avant d'ajouter cache, sessions
ou couches de retry.

Les bases sont supposées **pré-peuplées** par le pipeline d'ingestion (`data/`, hors de
cette stack) : les deux ne partagent que les bases.

## Les routes (ADR-030)

| Route | Rôle |
|---|---|
| `POST /api/v1/search`, corps `{ question, page?, pageSize? }` | Une page de la recherche : `{ page, pageCount, pageSize, pageSizes, results }` |
| `GET /api/v1/documents/:identifier` | Le texte entier d'un document, chargé à la demande : `{ identifier, title, content, contentLength }` |
| `POST /api/v1/explanations`, corps `{ selection, messages }` | La réponse du LLM sur les documents choisis, en flux SSE (voir « Les explications ») |
| `GET /api/v1/health` (alias `/health/services`) | Sonde TEI, OpenSearch, Mongo et le LLM |

La question passe dans le corps, jamais dans une URL : ni les logs d'accès ni un proxy
ne la gardent (ADR-010). Les logs n'en retiennent que la longueur.

Le contrat est dans `packages/contract/` (ADR-016), un sous-chemin par module :
`@murphy/contract/search` (la requête, la réponse, le document),
`@murphy/contract/explanations` (la requête d'explication) et `@murphy/contract/errors`
(la liste des codes d'erreur). Les réponses JSON gardent l'enveloppe
`{ status, data, meta }` de `buildApiResponse`.

## Le pipeline de recherche (`src/services/searchService.ts:searchDocuments`)

1. **Pagination** (`toPageWindow`, ADR-032 §8) — `pageSize` est l'une des tailles de
   `PAGINATION_SIZES` (`10,25,50` par défaut) : absente, la première ; toute autre, un 400
   `VALIDATION_ERROR` (champ `pageSize`). `page` (1 par défaut) donne
   `from = (page - 1) × pageSize`, `pageCount = ⌈PAGINATION_DEPTH / pageSize⌉`, et la
   dernière page est tronquée : `size = min(pageSize, PAGINATION_DEPTH − from)`.
   `from + size` ne dépasse jamais la profondeur, et aucun document classé n'est perdu.
   Une page au-delà de `pageCount` est refusée (`PAGE_OUT_OF_RANGE`) avant tout appel ;
   une page en deçà mais au-delà des documents trouvés rend une liste vide.
2. **Embedding** (`ragService.embedQuestion`) → service TEI. La consigne
   `EMBEDDING_QUERY_INSTRUCTION` est collée devant la question, sans séparateur : le
   modèle attend `Instruct: {tâche}\nQuery:` devant une question, et rien devant les
   passages indexés (ADR-031).
3. **Recherche** (`ragService.retrieveDocuments`) → OpenSearch, requête hybride (voir
   « La recherche ») : `size` documents classés à partir de `from`, avec
   leurs passages correspondants.
4. **Lecture des documents** (`ragService.fetchDocuments`) → MongoDB `documents`, par
   `identifier`. Le titre et le statut (`metadata.statut`, l'`ETAT` de la DILA) en
   viennent, et le texte de chaque passage est découpé dans le
   `content` de son document (`services/passages.ts`, voir « Le contrat avec
   l'ingestion »). Le `content` lui-même ne part pas au client.
5. **Réponse** — un résultat par document, dans l'ordre du classement : `identifier`,
   `title`, `documentType`, `nature`, `isInForce` et ses `passages` (`chunkId`, `text`,
   `start`, `end`). `isInForce` vaut `true` pour le statut `VIGUEUR` seul, `false` pour
   tout autre (`VIGUEUR_DIFF` compris), et manque sans statut, comme pour une décision
   (ADR-032 §9). Chaque résultat porte aussi `contentLength`. La réponse rappelle
   `pageSize`, les `pageSizes` permises et `contextBudget` (`LLM_CONTEXT_MAX_CHARS`), le
   budget de la jauge de la sélection. Aucun score ; les durées par étape sont journalisées (`Search completed`),
   pas renvoyées.

`GET /documents/:identifier` (`services/documentService.ts:readDocument`) lit un seul
document dans Mongo (`fetchDocument`) ; un identifiant inconnu donne
`DOCUMENT_NOT_FOUND`.

## Les explications (ADR-033)

`POST /api/v1/explanations` (`routes/explanations.ts`) : le client envoie les
identifiants de la sélection, dans son ordre, et le **segment courant** de la
conversation, c'est-à-dire les messages depuis le dernier changement de sélection. Le
serveur ne garde rien.

1. **Validation** (`validation/explanationRequest.ts`) : des documents sans doublon,
   ou aucun (le contexte dit alors « Aucun document sélectionné. » et le prompt fait
   inviter à en choisir) ; au moins un message, le dernier de l'utilisateur ; rôles `user` et
   `assistant` seulement.
2. **Lecture** (`MongoDbClient.fetchExplainedDocuments`) : chaque document relu dans
   Mongo, jamais le texte du client, dans l'ordre de la sélection ; un absent donne
   `DOCUMENT_NOT_FOUND`. La projection ne lit que les métadonnées de la liste blanche.
3. **Contexte** (`services/explanationContext.ts`) : chaque document derrière son repère
   `[n]`, avec son type, sa nature, son texte parent, les métadonnées de la liste blanche
   de sa source, libellées en français, et son texte entier. Les noms des magistrats et
   des avocats n'en font jamais partie (loi n° 2019-222, art. 33).
4. **Prompt** : `src/prompts/explanation.md`, versionné, lu au chargement et copié dans
   `dist/` au build. Il borne l'onglet : expliquer, sans qualifier ni conseiller.
5. **Budget** : prompt, documents et segment, comptés en points de code ; au-delà de
   `LLM_CONTEXT_MAX_CHARS`, un 400 `CONTEXT_TOO_LARGE`. Des questions consécutives
   (une réponse effacée par une erreur) sont fusionnées avant l'appel.
6. **Premier fragment** (`services/explanationService.ts:openAnswer`) : le backend
   attend le premier fragment pendant `LLM_TIMEOUT` au plus, avant d'ouvrir le flux. Une
   panne du LLM ou un délai dépassé donne donc un vrai 502 `LLM_FAILED` ou 504
   `TIMEOUT`.
7. **Flux** (`services/explanationStream.ts`) : le protocole SSE de l'AI SDK
   (`pipeUIMessageStreamToResponse`). Une erreur en cours de route devient un événement
   `error` qui ne porte que le code.

**L'arrêt se propage** : `res.on('close')` sans `res.writableEnded` lève un
`AbortSignal`, qui coupe l'appel au LLM. **Rien du contenu n'est journalisé** :
`Explanation completed` garde le nombre de documents, les longueurs, la durée, l'issue
(`completed`, `aborted`, `error`) et les tokens si le serveur les donne.

**Le LLM** (`infra/llm.ts`) : l'interface `LlmClient` a une seule opération,
`streamAnswer`. Son implémentation passe par `@ai-sdk/openai-compatible`, sans nouvelle
tentative (`maxRetries: 0`). Elle journalise une erreur du fournisseur par son nom et
son statut, jamais par son message. Aucun fournisseur n'est nommé : changer de serveur
change `LLM_BASE_URL`, pas le code.

Le LLM est **obligatoire** : sans `LLM_BASE_URL`, `LLM_API_KEY` ou `LLM_MODEL`, le
backend refuse de démarrer. Le démarrage ne le sonde pas : un fournisseur en panne ne se
révèle qu'à l'appel, et ne bloque pas la recherche.

## Le contrat avec l'ingestion (ADR-015)

L'ingestion et le serving ne partagent aucun code : leur contrat est écrit dans l'ADR-015.
Ce que le backend lit :

| Où | Quoi |
|---|---|
| Index OpenSearch `OPENSEARCH_INDEX` | `_source` : `identifier`, `document_type` (l'un des quatre types), `nature` (facultatif) ; `chunk_id`, `char_start`, `char_end` des passages dans les `inner_hits` — validé à la lecture (`infra/searchHits.ts`) |
| Mongo `MURPHY_DATA.documents` | `identifier`, `title`, `content`, `content_length` — un document **entier** par `identifier` (`infra/mongodb.ts`, `infra/documentRecords.ts`) ; pour les explications, aussi `document_type`, `nature`, `parent_text_title` et les métadonnées de la liste blanche |

- **Offsets** : `char_start`/`char_end` comptent des **points de code** (le `str` Python).
  `services/passages.ts` les convertit une fois en unités UTF-16 : `start` / `end` d'un
  passage se lisent directement avec `content.slice(start, end)` sur le texte servi par
  `GET /documents`.
- **`content_length`** : la longueur de `content` en points de code, écrite par
  l'ingestion. Absente (un corpus ingéré avant ADR-033), elle est une violation : il faut
  réingérer.
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
(`request`, `embedding`, `retrieval`, `generation`) ne sert qu'aux logs. Le code vaut `TIMEOUT` quand
le **type** de l'erreur se termine par `TimeoutError` (`AbortSignal.timeout`, client
OpenSearch, `MongoNetworkTimeoutError`…), sinon celui du client.

`utils/errorResponse.ts:toErrorResponse` donne le statut, et `errorHandler` répond :

| Statut | Codes |
|---|---|
| 400 | `VALIDATION_ERROR`, `INVALID_JSON`, `PAGE_OUT_OF_RANGE`, `CONTEXT_TOO_LARGE` |
| 404 | `DOCUMENT_NOT_FOUND`, `NOT_FOUND` (route inconnue) |
| 413 | `PAYLOAD_TOO_LARGE` |
| 4xx | `INVALID_REQUEST_BODY`, toute autre erreur du parseur, à son statut |
| 429 | `SEARCH_RATE_LIMIT_EXCEEDED`, `EXPLANATION_RATE_LIMIT_EXCEEDED`, `EXPLANATION_QUOTA_EXCEEDED`, `RATE_LIMIT_EXCEEDED` |
| 502 | `EMBEDDING_FAILED`, `SEARCH_FAILED`, `DB_FETCH_FAILED`, `LLM_FAILED` |
| 504 | `TIMEOUT` |
| 500 | `CONTRACT_VIOLATION`, `INTERNAL` (toute autre erreur) |

Un 4xx est journalisé en `warn`, le reste en `error`. Une recherche ne surveille pas le
départ du client : la réponse à un client parti est perdue, sans autre effet (ADR-030 §6).
Une explication, elle, coupe le LLM (ADR-033 §11).

## Clients d'infrastructure (`src/infra/`)

`EmbeddingClient` (TEI), `OpenSearchClient`, `MongoDbClient`, `LlmClient`. Chaque client
reçoit sa section de `config` (`src/config.ts`) ; aucun ne lit l'environnement.

`infra/clients.ts:initInfraClients(config)` les crée **une fois au boot**, avant
l'écoute (`server.ts`) : connexion Mongo, vérification de l'index OpenSearch et écriture
du pipeline RRF (`prepareSearch`), puis les clients TEI et LLM, sans sonde. Il peut
refuser le démarrage.
Les requêtes y accèdent par `getInfraClients()`, qui lève s'il est appelé avant
l'initialisation ; `closeInfraClients()` ferme Mongo au shutdown gracieux. Ne jamais
`new`-er un client par requête.

Délais par défaut : TEI, Mongo et OpenSearch 10 s (`OPENSEARCH_TIMEOUT` vaut pour la
recherche comme pour le boot), le LLM 30 s jusqu'au premier fragment (`LLM_TIMEOUT`),
sans relance.

**Fail-fast** : `utils/configWarnings.ts:checkEnvironment` refuse le démarrage dès qu'une
variable obligatoire manque (`MONGODB_URI`, `OPENSEARCH_INDEX`,
`EMBEDDING_QUERY_INSTRUCTION`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`).

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
  `express.json()` parse les corps : 100 Kio au plus, sauf pour `/explanations`, dont la
  limite découle du budget (`utils/requestLimits.ts`), pour qu'un long segment soit
  compté par le budget plutôt que refusé avant.
- **Ordre des middlewares** (`app.ts`) : requestLogger → helmet / rate-limit général /
  CORS (`middleware/security.ts`) → body parsing → routes → handlers d'erreur.
- **Quotas par IP** : le limiteur général (600 requêtes par 15 min, `RATE_LIMIT_*`) couvre
  toutes les routes ; `POST /search` ajoute `searchRateLimiter` (60 par minute,
  `SEARCH_RATE_LIMIT_*`), car chaque recherche appelle TEI et OpenSearch.
  `POST /explanations` ajoute deux plafonds (`middleware/explanationRateLimiter.ts`) :
  10 questions par minute et par IP (`EXPLANATION_RATE_LIMIT_*`), et 200 appels par jour
  tous clients confondus (`EXPLANATION_DAILY_LIMIT`, compteur en mémoire ; une requête
  refusée n'y compte pas). `trust proxy`
  vaut `false` (`app.ts`) tant qu'aucun proxy n'est placé devant le backend.
- **Santé** : `/api/v1/health`, latence par service — `ok` / `degraded` (1 service down)
  / `down` (2+), 503 si non-ok. Le LLM est sondé par `GET {LLM_BASE_URL}/models`,
  authentifié, qui ne génère rien.

## Dépendances externes

| Service | Rôle | Note |
|---|---|---|
| TEI (HuggingFace Text Embeddings Inference) | Embedding de la question | `POST /v1/embeddings`, GPU NVIDIA requis. Le modèle (`microsoft/harrier-oss-v1-0.6b`, 1024, Cosine) doit être celui de l'ingestion ; seule la question porte la consigne. |
| OpenSearch | Recherche hybride | Index `OPENSEARCH_INDEX`, vérifié au boot ; pipeline `murphy-rrf` écrit au boot. Sonde de santé : `/_cluster/health`. |
| MongoDB | Titre et texte des documents | Le texte des passages y est découpé ; `GET /documents` le sert entier. |
| LLM compatible OpenAI | Les explications | `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` ; un fournisseur externe pour l'instant : les questions et les documents choisis quittent le système. |
| Neo4j | — | Provisionné, **pas encore câblé** dans le chemin de requête (réservé : enrichissement graphe). |
