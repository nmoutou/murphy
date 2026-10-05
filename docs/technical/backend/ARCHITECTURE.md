# Architecture — backend de serving

## Ce que c'est

L'orchestrateur RAG de Murphy : une API Express 5 / TypeScript, **stateless par
conception** — chaque requête recompute tout le pipeline, aucun historique
conversationnel, aucune session, aucun retry automatique (fail-fast avec une erreur
claire, `RagError` portant `stage` = `embedding` | `retrieval` | `llm`). Garder cela en
tête avant d'ajouter cache, sessions ou couches de retry.

Les bases sont supposées **pré-peuplées** par le pipeline d'ingestion (`data/`, hors de
cette stack) : les deux ne partagent que les bases.

## Le pipeline RAG (`src/services/chatService.ts:createChatStream`)

1. **Extraction de la question** — dernier message `user`, parts `text` concaténées
   (`extractQuestionFromMessages`). La requête porte un tableau `messages` (format
   AI SDK), pas une chaîne `question`.
2. **Embedding** (`ragService.embedQuestion`) → service TEI.
3. **Recherche** (`ragService.retrieveDocuments`) → OpenSearch, requête hybride (voir
   « La recherche ») : `PAGINATION_SIZE` documents classés (défaut 10), avec leurs
   passages.
4. **Lecture des documents** (`ragService.fetchDocuments`) → MongoDB `documents`, par
   `identifier` (clé indexée). Le texte de chaque passage est découpé dans le
   `content` de son document, entre `char_start` et `char_end`
   (`services/passages.ts`, voir « Le contrat avec l'ingestion »).
5. **Streaming des sources** — **avant l'appel LLM** : pour chaque document, dans l'ordre du
   classement, une part `data-parentDocument` (le document entier) puis une part
   `data-document` par passage (le passage et ses bornes de surlignage). Une section n'a
   aucun passage : seule sa part `data-parentDocument` part, que le frontend n'affiche
   pas encore (ADR-028 §10).
6. **Streaming LLM** — contexte (le texte **des passages seuls**, pas des documents)
   injecté dans le system prompt (`config.llm.systemPrompt` : assistant juridique FR,
   surchargeable via `SYSTEM_PROMPT`), tokens de
   `getInfraClients().llm.stream()` écrits en parts `text-delta`. Le contexte est rempli
   dans l'ordre du classement et s'arrête avant le passage qui dépasserait **200 000
   caractères** (`MAX_LLM_CONTEXT_CHARS`) ; la coupe est journalisée en `warn`. Les
   sources, elles, partent toutes.
7. **Finish** — part `finish` avec `ragTiming` (latence par étape, en ms).

Le flux est construit avec le Vercel **AI SDK** (`createUIMessageStream` /
`pipeUIMessageStreamToResponse`). Le contrat de parts est `AppUIMessage`, importé de
`@murphy/contract/messages` (`packages/contract/`, ADR-016), que le frontend importe
aussi : parts custom `{ document: DocumentChunk; parentDocument: ParentDocument }`,
metadata `{ ragTiming }`. Le backend en importe les types, et `documentTypeSchema` pour valider l'index ; changer le contrat
casse la compilation des deux côtés à la fois.

### Trois transports, un seul pipeline

- **WebSocket** `/api/v1/chat/ws` (`routes/chatWebSocket.ts`) — ce que le frontend
  utilise. Un message entrant, un flux de parts JSON sortant, socket fermée. Une
  requête invalide ou un quota épuisé reçoivent une part `error` d'étape `request`, sans
  lancer le pipeline. `attachChatWebSocket` fixe les limites du socket : message de
  100 ko au plus (`maxPayload`, comme `express.json()`, `utils/requestLimits.ts`), en-tête
  `Origin` limité à `CORS_ORIGIN` (403 sinon ; un client sans `Origin` passe), fermeture
  en `1008` sans message après 10 s. Une trame invalide ou trop grosse est journalisée en
  `warn` et ferme ce seul socket : sans écouteur `error`, `ws` la lèverait en exception non
  capturée, qui arrête le serveur.
- **POST** `/api/v1/chat/streams` (SSE) et **POST** `/api/v1/chat/completions` (draine le
  flux en une réponse JSON) — `routes/chat.ts`, pour tests et clients non-WS.

Toute évolution du pipeline se fait dans `createChatStream` ; les trois chemins en
héritent.

### Erreurs et arrêt (ADR-017)

- **Une erreur dit l'étape, pas le détail.** Le `errorText` d'une part `error` est un
  `ChatError` sérialisé, `{ stage, code }` (`@murphy/contract/errors`) :
  - l'étape vaut `request`, `embedding`, `retrieval`, `llm` ou `internal` ;
  - `types/rag.ts:toChatError` la tire d'une `RagError`, et toute autre erreur devient
    `internal` ;
  - le message complet reste dans les logs, sans partir au client.
  - `/completions` renvoie ce même objet dans le `data` de son 500.
- **Le départ du client arrête le pipeline.** La fermeture du socket, ou celle de la
  réponse HTTP, lève le signal passé à `createChatStream`.
  - Le signal est vérifié avant le LLM, puis après lui.
  - `llm.stream` le transmet à son `fetch`, ce qui coupe la génération en cours.
  - Le flux s'arrête sans part `error` ni `finish`, et le backend logue « Chat stream
    aborted by the client ».

## Le contrat avec l'ingestion (ADR-015)

L'ingestion et le serving ne partagent aucun code : leur contrat est écrit dans l'ADR-015.
Ce que le backend lit :

| Où | Quoi |
|---|---|
| Index OpenSearch `OPENSEARCH_INDEX` | `_source` : `identifier`, `document_type` (l'un des quatre types), `nature` (facultatif), `passages` (`chunk_id`, `char_start`, `char_end`) ; les mêmes champs dans les `inner_hits` — validé à la lecture (`infra/searchHits.ts`) |
| Mongo `MURPHY_DATA.documents` | `identifier`, `title`, `content` — un document **entier** par `identifier` (`infra/mongodb.ts`) |

- **Offsets** : `char_start`/`char_end` comptent des **points de code** (le `str` Python).
  `services/passages.ts` les convertit une fois en unités UTF-16 : `highlightStart` /
  `highlightEnd` d'une part `data-document` se lisent directement avec
  `content.slice(highlightStart, highlightEnd)` côté client.
- **Violation** : un document OpenSearch sans champ du contrat, un document absent de
  Mongo ou des offsets hors de `content` lèvent une `RagError` `retrieval` /
  `CONTRACT_VIOLATION`. Son message, logué, cite l'`identifier` ou le `chunk_id`. La
  réponse s'arrête sur une part `error` : pas d'écart silencieux.

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
(défaut 100) ; seule la première page est servie (`from: 0`, ADR-028 §10).

**Les passages d'un document** (`services/passageRanking.ts`, ADR-028 §7) :
- ceux de la sous-requête lexicale (ses `inner_hits`, 100 au plus) et les 3 plus proches
  de la sous-requête vectorielle, fusionnés par RRF sur leurs rangs (constante 60, celle
  d'OpenSearch) et dédoublonnés par `chunk_id` ;
- un document trouvé sans passage correspondant (par son titre, ses métadonnées, son texte
  parent) les reçoit tous, lus dans son `_source`, dans l'ordre du texte.

Aucun score ne sort du backend : un score RRF n'est pas une similarité.

## Clients d'infrastructure (`src/infra/`)

`EmbeddingClient` (TEI), `OpenSearchClient`, `LLMProvider` (API OpenAI-compatible,
type Mammouth.AI), `MongoDbClient`. Chaque constructeur reçoit sa section de `config`
(`src/config.ts`) ; aucun ne lit l'environnement.

`infra/clients.ts:initInfraClients(config)` les crée **une fois au boot**, avant
l'écoute (`server.ts`) : connexion Mongo, vérification de l'index OpenSearch et écriture
du pipeline RRF (`prepareSearch`), puis les deux autres clients. Il peut refuser le démarrage.
Les requêtes y accèdent par `getInfraClients()`, qui lève s'il est appelé avant
l'initialisation ; `closeInfraClients()` ferme Mongo au shutdown gracieux. Ne jamais
`new`-er un client par requête.

**Erreurs** : chaque client traduit ses échecs par `types/rag.ts:toRagError(failure, error)`
en `RagError { stage, code }`. Le code vaut `TIMEOUT` quand le **type** de l'erreur se
termine par `TimeoutError` (`AbortSignal.timeout`, client OpenSearch,
`MongoNetworkTimeoutError`…), sinon le code propre au client (`NETWORK`,
`SEARCH_FAILED`, `DB_FETCH_FAILED`, `API_ERROR`). Délais par défaut : TEI et Mongo 10 s,
OpenSearch 10 s (`OPENSEARCH_TIMEOUT`, pour la recherche comme pour le boot, sans
relance), LLM 30 s. Le délai du LLM ne couvre que l'attente de la
réponse, pas le streaming qui suit.

## Conventions transverses

- **Réponses JSON** : `utils/response.ts:buildApiResponse(code, message, data?)` →
  `{ status: {code, message}, data?, meta: {timestamp, traceId} }` — pour toutes les
  réponses.
- **Logs** : Pino structuré (`utils/logger.ts`), un logger enfant par module
  (`rootLogger.child({ context: 'moduleName' })`).
- **Erreurs** : handlers async enveloppés par `middleware/errorHandler.ts:asyncHandler` ;
  `errorHandler` + `notFoundHandler` enregistrés en dernier dans `app.ts`. `errorHandler`
  rend leur statut 4xx aux erreurs `http-errors` marquées `expose`, celles du parseur
  JSON (`INVALID_JSON` 400, `PAYLOAD_TOO_LARGE` 413, sinon `INVALID_REQUEST_BODY`),
  journalisées en `warn` ; toute autre erreur est un `500 INTERNAL_ERROR`. Le message
  brut n'est jamais renvoyé. Seul `express.json()` parse les corps (pas de formulaires).
- **Ordre des middlewares** (`app.ts`) : requestLogger → helmet / rate-limit / CORS
  (`middleware/security.ts`) → body parsing → routes → handlers d'erreur. Les routes
  `/streams` et `/completions` ajoutent `streamRateLimiter`. Les trois transports valident
  la charge utile avec `validation/chatRequest.ts:parseChatRequest` (toute la forme
  `AppUIMessage` : `safeValidateUIMessages` de l'AI SDK, avec les schémas `data-*` et de
  métadonnées du contrat ; les erreurs ne recopient jamais la conversation reçue) et partagent le même
  budget de stream par IP (`consumeStreamQuota` côté WebSocket). `trust proxy` vaut `false` (`app.ts`) tant
  qu'aucun proxy n'est placé devant le backend.
- **Base path** : `/api/v1`. Santé : `/api/v1/health` (alias `/services`), latence par service — `ok` /
  `degraded` (1 service down) / `down` (2+), 503 si non-ok.

## Dépendances externes

| Service | Rôle | Note |
|---|---|---|
| TEI (HuggingFace Text Embeddings Inference) | Embedding de la question | `POST /v1/embeddings`, GPU NVIDIA requis. Le modèle (`all-mpnet-base-v2`, 768, Cosine) doit être celui de l'ingestion. |
| OpenSearch | Recherche hybride | Index `OPENSEARCH_INDEX`, vérifié au boot ; pipeline `murphy-rrf` écrit au boot. Sonde de santé : `/_cluster/health`. |
| MongoDB | Contenu des documents (contexte LLM) | |
| LLM | Génération | API OpenAI-compatible, streaming. |
| Neo4j | — | Provisionné, **pas encore câblé** dans le chemin de requête (réservé : enrichissement graphe). |
