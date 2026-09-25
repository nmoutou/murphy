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
4. **Streaming des sources d'abord** — chaque hit Qdrant est écrit comme part
   `data-document` **avant l'appel LLM** : l'UI affiche les sources immédiatement.
5. **Fetch du contenu** (`ragService.fetchChunkDocuments`) → MongoDB, par `chunkId`. Ce
   contenu ne sert qu'à construire le contexte LLM, jamais renvoyé tel quel au client.
6. **Streaming LLM** — contexte injecté dans le system prompt (`config.llm.systemPrompt` :
   assistant juridique FR, surchargeable via `SYSTEM_PROMPT`), tokens de
   `getInfraClients().llm.stream()` écrits en parts `text-delta`.
7. **Finish** — part `finish` avec `ragTiming` (latence par étape, en ms).

Le flux est construit avec le Vercel **AI SDK** (`createUIMessageStream` /
`pipeUIMessageStreamToResponse`). Le contrat de parts est `AppUIMessage`
(`src/types/messages.ts`) — à garder **synchronisé** avec
`frontend/src/types/messages.ts` : part custom `{ document: DocumentChunk }`, metadata
`{ ragTiming }`.

### Trois transports, un seul pipeline

- **WebSocket** `/api/v1/chat/ws` (`routes/chatWebSocket.ts`) — ce que le frontend
  utilise. Un message entrant, un flux de parts JSON sortant, socket fermée. Une
  requête invalide ou un quota épuisé reçoivent une part `error`, sans lancer le pipeline.
- **POST** `/api/v1/chat/streams` (SSE) et **POST** `/api/v1/chat/completions` (draine le
  flux en une réponse JSON) — `routes/chat.ts`, pour tests et clients non-WS.

Toute évolution du pipeline se fait dans `createChatStream` ; les trois chemins en
héritent.

## La résolution de collection Qdrant (`src/infra/collectionPointer.ts`)

Le pipeline d'ingestion nomme ses collections par une **empreinte** de sa config
(ex. `9424808d…`) et publie, à chaque run complet (`ok`), un **pointeur** dans Mongo
`MURPHY_META.meta_published_collection` (clé `current`). Au boot, le backend :

1. lit le pointeur (la vérité, publiée par un run complet) ;
2. à défaut, se replie sur `QDRANT_COLLECTION` — **bruyamment** (aucun run n'a encore
   publié) ;
3. dans les deux cas, **vérifie que la collection existe** dans Qdrant et refuse de
   démarrer sinon — mieux vaut le découvrir au boot que sur la première question d'un
   utilisateur.

## Clients d'infrastructure (`src/infra/`)

`EmbeddingClient` (TEI), `QdrantVectorClient`, `LLMProvider` (API OpenAI-compatible,
type Mammouth.AI), `MongoDbClient`. Chaque constructeur reçoit sa section de `config`
(`src/config.ts`) ; aucun ne lit l'environnement.

`infra/clients.ts:initInfraClients(config)` les crée **une fois au boot**, avant
l'écoute (`server.ts`) : connexion Mongo, résolution de la collection Qdrant publiée
(`collectionPointer.ts`), puis les trois autres clients. Il peut refuser le démarrage.
Les requêtes y accèdent par `getInfraClients()`, qui lève s'il est appelé avant
l'initialisation ; `closeInfraClients()` ferme Mongo au shutdown gracieux. Ne jamais
`new`-er un client par requête.

**Erreurs** : chaque client traduit ses échecs par `types/rag.ts:toRagError(failure, error)`
en `RagError { stage, code }`. Le code vaut `TIMEOUT` quand le **type** de l'erreur se
termine par `TimeoutError` (`AbortSignal.timeout`, `QdrantClientTimeoutError`,
`MongoNetworkTimeoutError`…), sinon le code propre au client (`NETWORK`,
`SEARCH_FAILED`, `DB_FETCH_FAILED`, `API_ERROR`). Le délai du LLM ne couvre que
l'attente de la réponse, pas le streaming qui suit.

## Conventions transverses

- **Réponses JSON** : `utils/response.ts:buildApiResponse(code, message, data?)` →
  `{ status: {code, message}, data?, meta: {timestamp, traceId} }` — pour toutes les
  réponses.
- **Logs** : Pino structuré (`utils/logger.ts`), un logger enfant par module
  (`rootLogger.child({ context: 'moduleName' })`).
- **Erreurs** : handlers async enveloppés par `middleware/errorHandler.ts:asyncHandler` ;
  `errorHandler` + `notFoundHandler` enregistrés en dernier dans `app.ts`.
- **Ordre des middlewares** (`app.ts`) : requestLogger → helmet / rate-limit / CORS
  (`middleware/security.ts`) → body parsing → routes → handlers d'erreur. La route de
  stream ajoute `streamRateLimiter`. Les deux transports valident la charge utile avec
  `validation/chatRequest.ts:parseChatRequest` et partagent le même budget de stream par
  IP (`consumeStreamQuota` côté WebSocket). `trust proxy` vaut `false` (`app.ts`) tant
  qu'aucun proxy n'est placé devant le backend.
- **Base path** : `/api/v1`. Santé : `/api/v1/health` (alias `/services`), latence par service — `ok` /
  `degraded` (1 service down) / `down` (2+), 503 si non-ok.

## Dépendances externes

| Service | Rôle | Note |
|---|---|---|
| TEI (HuggingFace Text Embeddings Inference) | Embedding de la question | `POST /v1/embeddings`, GPU NVIDIA requis. Le modèle (`all-mpnet-base-v2`, 768, Cosine) doit être celui de l'ingestion. |
| Qdrant | Recherche vectorielle | Collection résolue par le pointeur publié. |
| MongoDB | Contenu des documents (contexte LLM) + pointeur (base méta) | |
| LLM | Génération | API OpenAI-compatible, streaming. |
| Neo4j | — | Provisionné, **pas encore câblé** dans le chemin de requête (réservé : enrichissement graphe). |
