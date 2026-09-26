# Corrections — backend

> Périmètre : le dossier `backend/`. Chemins relatifs
> à `backend/`. Index et ordre d'exécution : [`README.md`](README.md).
>
> Les deux correctifs locaux relevés par l'audit sont commités par le
> porteur (`3b5d811`) :
> - `infra/collectionPointer.ts:24` lit `MONGODB_META_DB_NAME` ;
> - `routes/health.ts:53` sonde `/healthz`.
>
> **Premier lot** (BE-01, BE-02, BE-04, BE-05) : commité par le porteur
> (`8dda745`).
>
> **Deuxième lot exécuté le 25 septembre 2026** (BE-03, BE-12, BE-13,
> BE-14, BE-16), non commité : le sous-module reste en HEAD détachée sur
> `8dda745`.
>
> **Troisième lot exécuté le 25 septembre 2026** (BE-06, BE-08, BE-09),
> non commité, empilé sur le deuxième.
>
> **Quatrième lot exécuté le 25 septembre 2026** (TR-01 côté backend,
> BE-11, BE-15), non commité, sur `144d770`. Les numéros de ligne des items
> restants renvoient au code **d'avant** le premier lot.

## 1. Tableau

| ID | Point | Sévérité | Statut |
|---|---|---|---|
| BE-01 | 2 suites de tests sur 3 ne compilent plus | Bloquant | ✅ |
| BE-02 | 29 erreurs eslint | Bloquant | ✅ |
| BE-03 | Le rate-limiter de stream fait confiance à `X-Forwarded-For` — **décidé** | Dette (sécurité) | ✅ sans ADR (hygiène) |
| BE-04 | Route `GET /documents/:eli` morte et fausse — **décidé : suppression** | Dette | ✅ sans ADR (hygiène) |
| BE-05 | Code mort (liste §2.5) | Dette | ✅ |
| BE-06 | Barrel `infra/index.ts` + singletons `Proxy` typés `any` | Dette | ✅ |
| BE-07 | `llm.stream` : décodage et parsing sur-complexes, erreurs avalées | Dette | ✅ |
| BE-08 | Le même bloc `try/catch/log/RagError` est copié dans 4 clients | Dette | ✅ |
| BE-09 | Configuration dispersée : `process.env` lu dans 15 fichiers, nombres magiques | Dette | ✅ |
| BE-10 | Commentaires et métadonnées qui mentent | Dette | ✅ |
| BE-11 | Typage : `any`, casts, nom qui masque un global | Dette | ✅ |
| BE-12 | `dotenv` ne charge rien, `@types/ws` en dépendance runtime | Confort | ✅ |
| BE-13 | Le WebSocket ne valide pas son entrée | Dette | ✅ |
| BE-14 | `health.ts` : deux handlers identiques, un timer jamais annulé | Confort | ✅ |
| BE-15 | `chatService.createChatStream` : `execute` fait 49 lignes | Dette | ✅ |
| BE-16 | Le WebSocket n'a aucune limite de débit (trouvé pendant le lot 2) | Dette (sécurité) | ✅ |
| BE-17 | La fermeture du client n'arrête pas le pipeline : le LLM génère jusqu'au bout (trouvé avec FE-03) | Dette | ✅ [ADR-041](../../product/ADR/ADR-041-erreurs-du-chat-en-modale.md) |
| BE-18 | Le message brut d'une erreur part au client, sans l'étape en cause (trouvé avec FE-03) | Dette (sécurité) | ✅ [ADR-041](../../product/ADR/ADR-041-erreurs-du-chat-en-modale.md) |

🔶 : entamé ; le détail dit ce qui reste.

### Résultat du premier lot

| Contrôle | Avant | Après |
|---|---|---|
| `tsc --noEmit` | ✅ | ✅ |
| `npm run lint` | 29 erreurs | ✅ 0 |
| `npm test` | 2 suites / 3 ne compilent plus, 4 tests | ✅ 5 suites, 31 tests |
| `jest --coverage` | non mesurable | lignes 40 %, instructions 39 %, fonctions 36 %, branches 28 % — **sous les seuils** (65 / 65 / 60 / 40) |
| `npm run build` | ✅ | ✅ |

Les seuils de couverture n'ont été ni baissés ni contournés. Ils ne
s'appliquent qu'avec `--coverage` : `npm test` ne les vérifie pas. Les
modules sans aucun test sont `app.ts`, `health.ts`,
`collectionPointer.ts`, `chatWebSocket.ts`, `configWarnings.ts`,
`embedding.ts`, `qdrant.ts`, `mongodb.ts`, `security.ts` et
`requestLogger.ts`. Les tester, ou recadrer `collectCoverageFrom`, se
décide avec BE-06 et BE-09, qui réécrivent justement ces modules.

**Effet visible** : `messages.*.parts` est désormais obligatoire. Une
requête HTTP avec des messages sans `parts` reçoit un 400 au lieu d'une
réponse ; le repli sur `content` a été retiré avec le code mort. Le
frontend n'est pas touché, car `useChat` envoie toujours `parts`.

### Résultat du deuxième lot

| Contrôle | Après le lot 1 | Après le lot 2 |
|---|---|---|
| `tsc --noEmit` | ✅ | ✅ |
| `npm run lint` | ✅ 0 | ✅ 0 |
| `npm test` | 5 suites, 31 tests | ✅ 9 suites, 54 tests |
| `jest --coverage` (lignes / instructions / fonctions / branches) | 40 / 39 / 36 / 28 % | 66 / **64,5** / 60 / 46 % — seules les instructions restent sous le seuil de 65 % |
| `npm run build` | ✅ | ✅ |

Nouvelles suites : `validation/chatRequest`, `routes/chatWebSocket` (vrai
serveur WebSocket), `routes/health` et `middleware/streamRateLimiter`.
Cette dernière envoie 11 requêtes au vrai `app`, chacune avec un
`X-Forwarded-For` forgé différent. Elle échoue si l'on remet l'ancienne
clé fondée sur l'en-tête (contre-épreuve faite). Le code encore sans
test est surtout dans `infra/` (hors `llm.ts`) et `configWarnings.ts`,
que le lot 3 réécrit.

**Effets visibles** :
- `GET /api/v1/health` renvoie aussi `latencyMs` pour chaque service,
  comme `/services`, qui en devient un alias. Le changement est additif.
- Une part qui n'est pas un objet avec un `type` texte donne un 400 en
  HTTP.
- Sur le WebSocket, une requête invalide, un JSON illisible ou un quota
  épuisé reçoivent une part `error` explicite, sans lancer le pipeline.
- POST `/streams` et le WebSocket partagent le budget de 10 questions
  par minute et par IP.

### Résultat du troisième lot

| Contrôle | Après le lot 2 | Après le lot 3 |
|---|---|---|
| `tsc --noEmit` | ✅ | ✅ |
| `npm run lint` | ✅ 0 | ✅ 0 |
| `npm test` | 9 suites, 54 tests | ✅ 15 suites, 82 tests |
| `jest --coverage` (lignes / instructions / fonctions / branches) | 66 / 64,5 / 60 / 46 % | ✅ 90 / 90 / 85 / 86 % — **les quatre seuils sont tenus** |
| `npm run build` | ✅ | ✅ |

Nouvelles suites : `config`, `types/rag` (`toRagError`),
`infra/embedding`, `infra/qdrant`, `infra/collectionPointer` et
`infra/clients`. Contre-épreuve faite : si l'on remet la détection du
délai par sous-chaîne du message, 6 tests échouent. Restent sans test
`infra/mongodb.ts` (le pilote réel) et `utils/configWarnings.ts`.

`process.env` n'est plus lu que dans `src/config.ts`.

**Effets visibles** :
- Un nombre mal écrit dans l'environnement (`LLM_TEMPERATURE=abc`,
  `RETRIEVAL_TOP_K=2.5`) **bloque le démarrage**, avec un message qui
  nomme la variable. Avant, il devenait `NaN` sans rien signaler.
- Le journal de démarrage liste toutes les variables qui prennent leur
  valeur par défaut, y compris `MONGODB_META_DB_NAME` et `NODE_ENV`,
  que l'ancienne liste manuelle oubliait.
- Le code `TIMEOUT` d'un `RagError` dépend du type de l'erreur, plus de
  son texte. Un message qui contient « timeout » sans être un délai
  garde le code de l'étape.
- Le message de log d'un échec d'infrastructure est celui du
  `RagError`, par exemple `Failed to search Qdrant: …`, et l'erreur
  d'origine est sérialisée sous `err`.

**Constaté hors lot** : le client Qdrant garde son délai par défaut de
300 s. Aucune variable `QDRANT_TIMEOUT` ne le règle, ce qui contredit le
fail-fast du serving.

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
- ~~`tsconfig.json` : ajouter `"isolatedModules": true`~~ : **écarté à
  l'exécution**. Avec cette option, ts-jest passe en transpilation seule
  et ne vérifie plus les types des tests, que `tsc` exclut par ailleurs.
  L'avertissement TS151002 est donc réduit au silence dans
  `jest.config.js` (`diagnostics.ignoreCodes`) ; il concerne
  l'interopérabilité ESM, et le paquet est en CommonJS.

**Fait** :
- `chatService.test.ts` (nouveau) ;
- `ragService.test.ts` et `routes/chat.test.ts`, réécrits de zéro ;
- `infra/llm.test.ts` (nouveau) ;
- `errorHandler.test.ts`, passé à supertest.

Les chemins d'erreur, prérequis de FE-03, sont couverts : un échec du
LLM ou de l'embedding produit une part `error`. Les tests ne mockent que
les frontières (`infra`, `infra/mongodb`, le logger) et n'ont aucun
`any`.

### BE-02 — lint

29 erreurs `no-explicit-any` / `no-unused-vars`. La plupart disparaissent
avec BE-05, BE-06, BE-07 et BE-11. Les paramètres `_next` / `_req` exigés
par la signature Express se règlent dans `eslint.config.mjs`, avec
`argsIgnorePattern: '^_'`. La configuration actuelle n'importe que les
règles `recommended` sans le parser typé : passer au paquet
`typescript-eslint` (`tseslint.configs.recommended`).

**Fait** : `typescript-eslint` et `@eslint/js` remplacent
`@typescript-eslint/eslint-plugin` et `@typescript-eslint/parser`.
`eslint.config.mjs` combine `js.configs.recommended` et
`tseslint.configs.recommended`, avec `argsIgnorePattern` et
`caughtErrorsIgnorePattern` réglés sur `'^_'`. Les correctifs locaux des
`any` sont listés sous BE-06, BE-07, BE-08 et BE-11.

### BE-03 — `X-Forwarded-For` (décidé)

**Fait (lot 2)** :
- `app.ts` fixe `trust proxy` à `false` : pas de proxy tant que le
  backend n'est pas déployé (TR-03). Derrière un proxy, il faudra y mettre
  le nombre de sauts.
- Le `keyGenerator` et le `skip` sont supprimés. La clé par défaut,
  `ipKeyGenerator(req.ip)`, s'applique.
- Pas d'ADR : décision du porteur, traitée comme de l'hygiène.

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

**Fait (correctif minimal, en attendant la cible)** : les ré-exports
sans importeur sont retirés. `infra/index.ts` ne contient plus que les
trois singletons et `initQdrantClient`. `(x as any)[prop]` devient
`Reflect.get(x, prop)`.

**Cible** : un module `infra/clients.ts`, créé à `start()` à partir de la
configuration de BE-09, qui expose des instances typées. Les imports
passent directement par les fichiers sources. Cascade : `server.ts`,
`ragService.ts`, `chatService.ts`, les tests et `CLAUDE.md`.

**Fait (lot 3)** :
- `infra/index.ts` est supprimé.
- `infra/clients.ts:initInfraClients(config)`, appelé par `start()`,
  connecte Mongo, résout la collection publiée, puis crée les autres
  clients.
- `getInfraClients()` les expose, typés, et lève s'il est appelé avant
  l'initialisation.
- `closeInfraClients()` ferme Mongo à l'arrêt.
- `MongoDbClient.connect(config)` renvoie un client déjà connecté : les
  états `null` et le singleton de module disparaissent.
- `collectionPointer.ts` reçoit le client Mongo et la configuration en
  paramètres.

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

**Fait** :
- Décodage : `pipeThrough(new TextDecoderStream())`. Cela corrige un
  **bug réel**. Chaque morceau réseau était décodé seul, donc un
  caractère accentué coupé entre deux morceaux devenait `�`. Le test
  `llm.test.ts` échoue sur l'ancien code et passe sur le nouveau.
- L'extraction du token est sortie dans `extractToken`.
- Une ligne non-JSON est journalisée au niveau `debug`.

- `stream` repasse sous 30 lignes au lot 3 : le découpage en lignes est
  sorti dans `readLines`.
- Seul `delta.content` est lu ; `delta.text` et `text.content` sont
  retirés. Un appel en streaming à Mammouth (`llama-4-maverick`) l'a
  vérifié le 26 septembre 2026 : ses chunks ne portent que `delta.role` et
  `delta.content`. Un test fixe ce comportement.

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

Dans le premier lot, seul `(error as any)?.name` est remplacé, dans les
4 clients, par `error instanceof Error ? error.name : undefined`. Le
bloc dupliqué reste. `health.ts` utilise déjà `AbortSignal.timeout`
(lot 2, BE-14).

**Fait (lot 3)** :
- `types/rag.ts:toRagError(failure, error)` est la seule traduction. Le
  code vaut `TIMEOUT` quand le nom de l'erreur se termine par
  `TimeoutError`, ce qui couvre `AbortSignal.timeout`,
  `QdrantClientTimeoutError`, `MongoNetworkTimeoutError` et
  `MongoOperationTimeoutError`. Sinon, c'est le code de l'étape.
- Le nom est lu sans passer par `instanceof Error`, car une
  `DOMException` venue d'un autre realm (le bac à sable de Jest) échoue
  à ce test.
- Chaque client déclare sa constante `RagFailure`, et son `catch` tient
  en trois lignes.
- `embedding.ts` passe à `AbortSignal.timeout`. Une garde remplace le
  cast de la réponse TEI.
- `llm.ts` garde un `AbortController`, annulé une fois la réponse reçue :
  le délai ne couvre que l'attente de la réponse. `AbortSignal.timeout`
  couperait aussi une longue réponse en cours de streaming. Le contrôleur
  interrompt la requête avec une `TimeoutError` pour que le code soit
  bien `TIMEOUT`.

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

**Fait (lot 3)** :
- `src/config.ts:loadConfig(env)` renvoie `{ config, report }`, découpé
  par section (`server`, `http`, `mongo`, `qdrant`, `embedding`, `llm`,
  `retrieval`), avec toutes les valeurs par défaut en constantes nommées.
- Une valeur vide vaut une variable absente : Compose passe `VAR=`.
- Un nombre invalide lève une erreur qui nomme la variable.
- Le lecteur enregistre les variables manquantes et celles qui ont pris
  leur valeur par défaut. `checkEnvironment(report)` journalise ce
  rapport, et les listes manuelles disparaissent.
- Le prompt système par défaut passe de `ragService` à `config.ts`.
- Les autres nombres magiques deviennent des constantes :
  `MONGO_MAX_POOL_SIZE` et `FORCED_SHUTDOWN_DELAY_MS`.

### BE-10 — commentaires et métadonnées faux

| Emplacement | Écrit | Réalité |
|---|---|---|
| ~~`package.json:4`~~ | ~~« Backend service with Temporal workflow orchestration »~~ | ✅ corrigé |
| ~~`routes/chat.ts:21-33`~~ | ~~`POST /api/chat/stream`, corps `{ id, question, history }`…~~ | ✅ corrigé, et `/completions` est documentée |
| ~~`middleware/streamRateLimiter.ts:3`, l. 13~~ | ~~`/api/chat/stream`, « SSE streaming endpoint »~~ | ✅ corrigé |
| ~~`infra/llm.ts:89`~~ | ~~« Stream completions from Mammouth API »~~ | ✅ corrigé |
| ~~`infra/mongodb.ts:151`~~ | ~~paramètre `elis`~~ | ✅ renommé `chunkIds` |
| ~~`infra/embedding.ts:42`~~ | ~~« 768-dimensional »~~ | ✅ corrigé (lot 3) |

### BE-11 — typage

- ✅ (lot 4) `types/rag.ts:24` : `interface Document` masque le type global DOM
  `Document`. Remplacé, avec `SearchResult` et son payload lâche, par les
  types du contrat ADR-039 : `RetrievedChunk` (point Qdrant validé),
  `StoredDocument` (document parent Mongo) et `Passage`. Les casts
  `as string` sur le payload disparaissent de `chatService.ts`.
- ✅ `types/rag.ts:44` : `[key: string]: any` → `unknown`.
- ✅ `middleware/validation.ts:13` : `(err as any).path` → restreindre
  avec `err.type === 'field'`.
- ✅ `routes/chat.ts:69` : le cast `value as { type; delta?; errorText? }`
  est supprimé, puisque `value` est déjà typé `UIMessageChunk`.
- ✅ `infra/qdrant.ts:53` : `(point: any)` → le type est inféré depuis
  `@qdrant/js-client-rest`.
- ✅ `routes/chat.ts:42,62`, `routes/chatWebSocket.ts:15` : `messages || []`
  laisse passer une liste vide jusqu'à `createChatStream`, qui lève alors
  « No question provided ». Rejeter en 400 à la validation. Fait avec
  BE-13 : `validation/chatRequest.ts` refuse une liste vide.

### BE-12 — dépendances et amorçage

**Fait (lot 2)** : `dotenv` est supprimé, car l'environnement vient de
Compose ou doit être exporté à la main. `@types/ws` est passé en
`devDependencies`. `express-validator` est aussi retiré (BE-13).

- `server.ts:12` : `dotenv.config()` cherche `backend/.env`, qui n'existe
  pas (le fichier unique est `.env.dev` à la racine), et ne charge donc
  **rien**. C'est le même no-op silencieux que celui retiré de
  `data/src/data/settings.py`. Soit supprimer `dotenv`, soit pointer
  explicitement sur `../.env.dev` pour le mode sans Docker.
- `package.json` : `@types/ws` est dans `dependencies` et doit passer en
  `devDependencies`.

### BE-13 — WebSocket sans validation

**Fait (lot 2)** : nouvelle fonction pure `validation/chatRequest.ts:parseChatRequest`,
utilisée par `routes/chat.ts` et `routes/chatWebSocket.ts`. Elle remplace
`express-validator` et `middleware/validation.ts`. Elle vérifie aussi que
chaque part est un objet avec un `type` texte. Le listener WebSocket
capte désormais ses propres rejets : avant, un `ws.send` qui levait dans
le `catch` devenait un rejet non géré, que `server.ts` traite par un
arrêt du serveur.

`routes/chatWebSocket.ts:14` fait `JSON.parse` puis un cast direct en
`{ messages?: AppUIMessage[] }`. `chatValidation` ne protège que les
routes HTTP. Valider la charge utile à cette frontière avec les mêmes
règles, extraites en une fonction pure réutilisée par les deux
transports.

### BE-14 — `health.ts`

**Fait (lot 2)** : un seul handler, monté sur `/` et `/services`.
`AbortSignal.timeout` remplace le couple `AbortController`/`setTimeout`
dans `checkHttpService`. Le timer du ping Mongo est annulé dans un
`finally`. Le délai de 3 s est une constante nommée.

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

**Fait (lot 4)**, avec TR-01 : `execute` fait 20 lignes utiles. `writeSources`
écrit chaque document parent une fois, avant son premier passage ;
`buildLlmMessages` et `streamAnswer` sont extraits. `createChatStream` a
un type de retour explicite.

### BE-16 — WebSocket sans limite de débit

Trouvé pendant le lot 2. Les limiteurs (global et stream) sont des
middlewares Express : ils ne s'appliquent pas à la requête d'upgrade du
WebSocket. Or c'est le seul transport qu'utilise le frontend. Il
n'avait donc **aucune** limite.

**Fait (lot 2)** : `streamRateLimiter.ts` expose `consumeStreamQuota`,
qui compte chaque message WebSocket dans le même `MemoryStore` que le
limiteur HTTP. POST `/streams` et le WebSocket partagent le budget, et
un quota épuisé reçoit une part `error`. Le limiteur global
(100 requêtes / 15 min) ne couvre toujours pas le WebSocket, mais le
budget de stream, plus strict, suffit.

### BE-17 — l'arrêt n'atteint pas le pipeline

Trouvé en préparant FE-03. Fermer le WebSocket annulait la lecture du
flux (`reader.cancel()`), mais `createUIMessageStream` n'interrompt pas
`execute` : ses écritures sont avalées par `safeEnqueue`, et le LLM
générait jusqu'au bout. Le bouton d'arrêt du frontend n'arrêtait donc
que l'affichage.

**Fait (26 septembre 2026, ADR-041)** :
- `createChatStream` reçoit un `AbortSignal`, que lève la fermeture du
  socket ou de la réponse HTTP ;
- le signal est vérifié avant le LLM et après lui ;
- `llm.stream` le transmet à son `fetch`, puis se termine sans erreur.
- Vérifié sur la stack de dev : socket fermé en pleine réponse, le
  backend logue « Chat stream aborted by the client », sans « Chat
  stream finished ».

### BE-18 — message brut envoyé au client

`onError` et `streamAnswer` renvoyaient `err.message` au client, par
exemple `Failed to search Qdrant: connect ECONNREFUSED …`. L'étape en
cause, connue par `RagError.stage`, était perdue.

**Fait (26 septembre 2026, ADR-041)** :
- `errorText` porte un `ChatError` sérialisé, `{ stage, code }`
  (`@murphy/contract/errors`), construit par `types/rag.ts:toChatError` ;
- une erreur qui n'est pas une `RagError` devient `internal` ;
- le détail reste dans les logs.
