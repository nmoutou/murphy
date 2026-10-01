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
3. **Retrieval** (`ragService.retrieveChunks`) → Qdrant, top-K (`RETRIEVAL_TOP_K`,
   défaut 5), seuil `RETRIEVAL_MIN_SCORE` (défaut 0.5).
4. **Lecture des passages** (`ragService.fetchPassages`) → MongoDB `documents`, par
   `identifier` (clé indexée). Le texte de chaque passage est découpé dans le
   `content` de son document parent, entre `char_start` et `char_end`
   (`services/passages.ts`, voir « Le contrat avec l'ingestion »).
5. **Streaming des sources** — **avant l'appel LLM** : pour chaque passage, dans l'ordre du
   classement, une part `data-parentDocument` (le document entier, **une fois** par
   document, avant son premier passage) puis une part `data-document` (le passage et ses
   bornes de surlignage).
6. **Streaming LLM** — contexte (le texte **des passages seuls**, pas des documents)
   injecté dans le system prompt (`config.llm.systemPrompt` : assistant juridique FR,
   surchargeable via `SYSTEM_PROMPT`), tokens de
   `getInfraClients().llm.stream()` écrits en parts `text-delta`.
7. **Finish** — part `finish` avec `ragTiming` (latence par étape, en ms).

Le flux est construit avec le Vercel **AI SDK** (`createUIMessageStream` /
`pipeUIMessageStreamToResponse`). Le contrat de parts est `AppUIMessage`, importé de
`@murphy/contract/messages` (`packages/contract/`, ADR-040), que le frontend importe
aussi : parts custom `{ document: DocumentChunk; parentDocument: ParentDocument }`,
metadata `{ ragTiming }`. Le backend n'en importe que les types ; changer le contrat
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

### Erreurs et arrêt (ADR-041)

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

## Le contrat avec l'ingestion (ADR-039)

L'ingestion et le serving ne partagent aucun code : leur contrat est écrit dans l'ADR-039.
Ce que le backend lit :

| Où | Quoi |
|---|---|
| Payload Qdrant | `chunk_id`, `identifier`, `char_start`, `char_end`, `type_document` (facultatif) — validé à la lecture (`infra/qdrant.ts`) |
| Mongo `MURPHY_DATA.documents` | `identifier`, `title`, `content` — un document **entier** par `identifier` (`infra/mongodb.ts`) |

- **Offsets** : `char_start`/`char_end` comptent des **points de code** (le `str` Python).
  `services/passages.ts` les convertit une fois en unités UTF-16 : `highlightStart` /
  `highlightEnd` d'une part `data-document` se lisent directement avec
  `content.slice(highlightStart, highlightEnd)` côté client.
- **Violation** : un point sans champ du contrat, un document parent absent ou des offsets
  hors de `content` lèvent une `RagError` `retrieval` / `CONTRACT_VIOLATION`. Son message,
  logué, cite le `chunk_id`. La réponse s'arrête sur une part `error` : pas d'écart
  silencieux.

## La collection Qdrant

Son nom est **fixe** : `QDRANT_COLLECTION`, la variable que l'ingestion lit dans le même
`.env.dev` (ADR-042). Au boot, `QdrantVectorClient.assertCollectionExists()` **refuse de
démarrer** si Qdrant est injoignable ou si la collection n'existe pas : mieux vaut le
découvrir au boot que sur la première question d'un utilisateur.

## Clients d'infrastructure (`src/infra/`)

`EmbeddingClient` (TEI), `QdrantVectorClient`, `LLMProvider` (API OpenAI-compatible,
type Mammouth.AI), `MongoDbClient`. Chaque constructeur reçoit sa section de `config`
(`src/config.ts`) ; aucun ne lit l'environnement.

`infra/clients.ts:initInfraClients(config)` les crée **une fois au boot**, avant
l'écoute (`server.ts`) : connexion Mongo, vérification de la collection Qdrant
(`assertCollectionExists`), puis les deux autres clients. Il peut refuser le démarrage.
Les requêtes y accèdent par `getInfraClients()`, qui lève s'il est appelé avant
l'initialisation ; `closeInfraClients()` ferme Mongo au shutdown gracieux. Ne jamais
`new`-er un client par requête.

**Erreurs** : chaque client traduit ses échecs par `types/rag.ts:toRagError(failure, error)`
en `RagError { stage, code }`. Le code vaut `TIMEOUT` quand le **type** de l'erreur se
termine par `TimeoutError` (`AbortSignal.timeout`, `QdrantClientTimeoutError`,
`MongoNetworkTimeoutError`…), sinon le code propre au client (`NETWORK`,
`SEARCH_FAILED`, `DB_FETCH_FAILED`, `API_ERROR`). Délais par défaut : TEI et Mongo 10 s,
Qdrant 10 s (`QDRANT_TIMEOUT`, pour la recherche comme pour la vérification au boot ; le
client seul attendrait 300 s), LLM 30 s. Le délai du LLM ne couvre que l'attente de la
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
| Qdrant | Recherche vectorielle | Collection `QDRANT_COLLECTION`, vérifiée au boot. |
| MongoDB | Contenu des documents (contexte LLM) | |
| LLM | Génération | API OpenAI-compatible, streaming. |
| Neo4j | — | Provisionné, **pas encore câblé** dans le chemin de requête (réservé : enrichissement graphe). |
