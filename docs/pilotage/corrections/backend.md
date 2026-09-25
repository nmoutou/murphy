# Corrections — backend

> Périmètre : `backend/` (sous-module `murphy-backend`). Chemins relatifs
> à `backend/`. Index et ordre d'exécution : [`README.md`](README.md).
>
> **Modifications locales non commitées, à conserver** :
> - `infra/collectionPointer.ts:24` lit `MONGODB_META_DB_NAME`, le nom que
>   compose fournit réellement (`docker-compose.base.yml:58`) ;
> - `routes/health.ts:53` sonde `/healthz`, l'endpoint de santé de Qdrant.
>
> Ce sont deux correctifs justes, à commiter tels quels.

## 1. Tableau

| ID | Point | Sévérité | Statut |
|---|---|---|---|
| BE-01 | 2 suites de tests sur 3 ne compilent plus | Bloquant | ⬜ |
| BE-02 | 29 erreurs eslint | Bloquant | ⬜ |
| BE-03 | Le rate-limiter de stream fait confiance à `X-Forwarded-For` — **décidé** | Dette (sécurité) | ⬜ mini-ADR |
| BE-04 | Route `GET /documents/:eli` morte et fausse — **décidé : suppression** | Dette | ⬜ mini-ADR |
| BE-05 | Code mort (liste §2.5) | Dette | ⬜ |
| BE-06 | Barrel `infra/index.ts` + singletons `Proxy` typés `any` | Dette | ⬜ cascade |
| BE-07 | `llm.stream` : décodage et parsing sur-complexes, erreurs avalées | Dette | ⬜ |
| BE-08 | Le même bloc `try/catch/log/RagError` est copié dans 4 clients | Dette | ⬜ cascade |
| BE-09 | Configuration dispersée : `process.env` lu dans 15 fichiers, nombres magiques | Dette | ⬜ cascade |
| BE-10 | Commentaires et métadonnées qui mentent | Dette | ⬜ |
| BE-11 | Typage : `any`, casts, nom qui masque un global | Dette | ⬜ |
| BE-12 | `dotenv` ne charge rien, `@types/ws` en dépendance runtime | Confort | ⬜ |
| BE-13 | Le WebSocket ne valide pas son entrée | Dette | ⬜ |
| BE-14 | `health.ts` : deux handlers identiques, un timer jamais annulé | Confort | ⬜ |
| BE-15 | `chatService.createChatStream` : `execute` fait 49 lignes | Dette | ⬜ |

## 2. Détail

### BE-01 — tests qui ne compilent plus

`__tests__/services/ragService.test.ts` et `__tests__/routes/chat.test.ts`
importent `buildRagContext` et `MammouthProvider`, qui n'existent plus, et
construisent des `RagError` littéraux sans `name`. Les tests qui passent
(4) ne couvrent que `errorHandler`, si bien que les seuils de
`jest.config.js` ne mesurent rien.

- Réécrire les deux suites contre l'API actuelle : `createChatStream` (en
  mockant `embedQuestion`, `retrieveChunks`, `fetchChunkDocuments` et
  `llmProvider.stream`), `extractQuestionFromMessages`,
  `buildContextString`, puis les routes `/streams` et `/completions` avec
  supertest.
- Couvrir aussi le chemin d'erreur : un stage qui lève doit produire une
  part `error` (prérequis de FE-03).
- `tsconfig.json` : ajouter `"isolatedModules": true`, qui supprime
  l'avertissement ts-jest TS151002 émis à chaque exécution.

### BE-02 — lint

29 erreurs `no-explicit-any` / `no-unused-vars`. La plupart disparaissent
avec BE-05, BE-06, BE-07 et BE-11. Les paramètres `_next` / `_req` exigés
par la signature Express se règlent dans `eslint.config.mjs`, avec
`argsIgnorePattern: '^_'`. La configuration actuelle n'importe que les
règles `recommended` sans le parser typé : passer au paquet
`typescript-eslint` (`tseslint.configs.recommended`).

### BE-03 — `X-Forwarded-For` (décidé)

`middleware/streamRateLimiter.ts:22-31` prend comme clé le premier
élément de `X-Forwarded-For`, un en-tête que le client contrôle. Il suffit
de le forger à chaque requête pour contourner la limite (10 requêtes par
minute).

- Supprimer le `keyGenerator` et régler `app.set('trust proxy', …)` dans
  `app.ts`. La valeur dépend du déploiement (TR-03) : `false` sans proxy,
  sinon le nombre de sauts. La clé par défaut, `req.ip`, devient alors
  correcte, pour ce limiteur comme pour le limiteur global de
  `middleware/security.ts`.
- Supprimer au passage le `skip` (l. 49-53) : le limiteur est monté sur
  `/api/v1/chat/streams`, donc `req.path === '/health'` n'est jamais vrai.
  La variable `STREAM_RATE_LIMIT_SKIP_HEALTH` disparaît avec lui.

### BE-04 — `routes/documents.ts` (décidé : suppression)

Aucun appelant. La route interroge `MONGODB_COLLECTION` sur des champs
qu'aucune ingestion n'écrit plus (`eli`, `document_type`, `titrefull`,
`titre`, `num`, `chunk_index`). Supprimer le fichier et son montage
(`app.ts:8,39`).

### BE-05 — code mort

| Élément | Emplacement | Pourquoi mort |
|---|---|---|
| `LLMProvider.complete()` | `infra/llm.ts:191-223` | aucun appelant (`/completions` draine le stream) |
| `LLMProvider.getConfig()` | `infra/llm.ts:228-236` | aucun appelant |
| `top_p`, `frequency_penalty` | `infra/llm.ts:20-21` | jamais renseignés |
| `EmbeddingClient.embedTexts()` | `infra/embedding.ts:115-177` | aucun appelant ; doublon ligne à ligne de `embedText` |
| `getDocumentCount` | `infra/mongodb.ts:129-138,152` | aucun appelant |
| `createLogger` | `utils/logger.ts:44-46` | aucun appelant |
| `AppError`, `isOperational` | `middleware/errorHandler.ts:8-27` | jamais levée : `errorHandler` se réduit au cas 500 |
| ré-exports | `services/ragService.ts:74` (`RagError`), `routes/chat.ts:16` (`createChatStream`), `infra/mongodb.ts:144` (`mongoDbClient` exporté), l'export `default` doublant l'export nommé de `logger` | aucun importeur |
| repli `content` sans `parts` | `services/chatService.ts:33` | un `UIMessage` de l'AI SDK v6 porte toujours `parts` |
| paramètre par défaut `topK = 10` | `infra/qdrant.ts:37` | l'unique appelant passe toujours `topK` |

### BE-06 — barrel et `Proxy`

`infra/index.ts` est un barrel, que `CLAUDE.md` interdit. Ses trois
`Proxy` accèdent à l'instance via `as any` (l. 32, 53, 60). Le `Proxy`
sert seulement à différer la construction ; or `server.ts` initialise
déjà Mongo et Qdrant explicitement au boot.

**Cible** : un module `infra/clients.ts`, créé à `start()` à partir de la
configuration de BE-09, qui expose des instances typées. Les imports
passent directement par les fichiers sources. Cascade : `server.ts`,
`ragService.ts`, `chatService.ts`, les tests et `CLAUDE.md`.

### BE-07 — `llm.stream`

- `infra/llm.ts:110-128` : le corps de `fetch` est un
  `ReadableStream<Uint8Array>`. Quatre branches de décodage (`string`,
  `Buffer`, `Uint8Array`, `String()`) sous un `try/catch` qui ne peut pas
  lever, plus un `as any`. À remplacer par
  `response.body.pipeThrough(new TextDecoderStream())`.
- l. 152 : `json.choices?.[0]?.text?.content` ne correspond à aucun format
  d'API OpenAI-compatible. Ne garder que `delta.content`.
- l. 157-159 : une ligne JSON invalide est avalée sans trace. La
  journaliser au niveau `debug`.
- La fonction fait 90 lignes : extraire le découpage SSE (`splitSseLines`)
  et l'extraction du token.

### BE-08 — gestion d'erreur dupliquée

`embedding.ts`, `qdrant.ts`, `mongodb.ts` et `llm.ts` répètent le même
bloc : mesure de durée, `errorMessage`, `(error as any)?.name`, log, puis
`new RagError(stage, …)`. Le code d'erreur y est deviné **en cherchant une
sous-chaîne dans le message** (`includes('abort')`, `includes('timeout')`
ou `includes('Timeout')`).

- Utiliser `AbortSignal.timeout(ms)` au lieu du couple
  `AbortController` + `setTimeout` + `clearTimeout` (ce couple apparaît
  aussi dans `health.ts`).
- Classer par `error.name === 'TimeoutError'` plutôt que par le texte.
- Écrire une seule fonction `toRagError(stage, error)` dans `types/rag.ts`,
  utilisée par les 4 clients.

### BE-09 — configuration centralisée

`process.env` est lu dans 15 fichiers, avec des replis dupliqués :
- `'http://qdrant:6333'` à 3 endroits ;
- `'http://embedding-service:80'` à 2 endroits ;
- `'chunks'` à 5 endroits.

S'y ajoutent des nombres magiques : `10000`, `30000`, `0.7`, `1000`,
`0.5`, `3000` ×2, `900000`, `100`, `60000`, `10`, `maxPoolSize: 10`, et le
délai de 10 s de l'arrêt forcé. `RETRIEVAL_TOP_K` est re-parsé à chaque
requête (`chatService.ts:55`). `utils/configWarnings.ts` maintient à la
main une liste qui a déjà dérivé : `MONGODB_META_DB_NAME` en est absent.

**Cible** : `config.ts` lit et valide l'environnement une fois au boot, à
la frontière du système, et expose un objet `readonly` avec des
constantes nommées. `checkEnvironment` en dérive. Les constructeurs
reçoivent leur configuration au lieu de lire `process.env` dans leurs
paramètres par défaut.

### BE-10 — commentaires et métadonnées faux

| Emplacement | Écrit | Réalité |
|---|---|---|
| `package.json:4` | « Backend service with Temporal workflow orchestration » | aucun Temporal |
| `routes/chat.ts:21-33` | `POST /api/chat/stream`, corps `{ id, question, history }`, événements `start/token/end` | `POST /api/v1/chat/streams`, corps `{ messages }`, parts de l'AI SDK |
| `middleware/streamRateLimiter.ts:3`, l. 13 | `/api/chat/stream`, « SSE streaming endpoint » | `/api/v1/chat/streams` |
| `infra/llm.ts:89` | « Stream completions from Mammouth API » | fournisseur OpenAI-compatible quelconque |
| `infra/mongodb.ts:151` | paramètre `elis` | ce sont des `chunkIds` |
| `infra/embedding.ts:42` | « 768-dimensional » | dépend du modèle configuré |

### BE-11 — typage

- `types/rag.ts:24` : `interface Document` masque le type global DOM
  `Document`. Renommer en `ChunkDocument` (le nom définitif dépend de
  TR-01).
- `types/rag.ts:44` : `[key: string]: any` → `unknown`.
- `middleware/validation.ts:13` : `(err as any).path` → restreindre avec
  `err.type === 'field'`.
- `routes/chat.ts:69` : `value as { type; delta?; errorText? }` → `value`
  est déjà typé `UIMessageChunk`, le cast est inutile.
- `routes/chat.ts:42,62`, `routes/chatWebSocket.ts:15` : `messages || []`
  laisse passer une liste vide jusqu'à `createChatStream`, qui lève alors
  « No question provided ». Rejeter en 400 à la validation.

### BE-12 — dépendances et amorçage

- `server.ts:12` : `dotenv.config()` cherche `backend/.env`, qui n'existe
  pas (le fichier unique est `.env.dev` à la racine), et ne charge donc
  **rien**. C'est le même no-op silencieux que celui retiré de
  `data/src/data/settings.py`. Soit supprimer `dotenv`, soit pointer
  explicitement sur `../.env.dev` pour le mode sans Docker.
- `package.json` : `@types/ws` est dans `dependencies` et doit passer en
  `devDependencies`.

### BE-13 — WebSocket sans validation

`routes/chatWebSocket.ts:14` fait `JSON.parse` puis un cast direct en
`{ messages?: AppUIMessage[] }`. `chatValidation` ne protège que les
routes HTTP. Valider la charge utile à cette frontière avec les mêmes
règles, extraites en une fonction pure réutilisée par les deux
transports.

### BE-14 — `health.ts`

- `GET /` et `GET /services` ne diffèrent que par `withLatency` : un seul
  handler suffit, qui mesure toujours la latence.
- `checkMongoDB` : le `setTimeout` de `Promise.race` n'est jamais annulé.
- `checkHttpService` : `clearTimeout` est dupliqué dans le `try` et le
  `catch`. Les deux disparaissent avec `AbortSignal.timeout` (BE-08).

### BE-15 — `createChatStream`

Le callback `execute` fait 49 lignes utiles (limite de `CLAUDE.md` : 30). Extraire :
- `writeSources(writer, results)` ;
- `buildLlmMessages(question, documents)` ;
- `streamAnswer(writer, messages)`.

À faire **après TR-01**, qui change le contenu de chaque étape.
