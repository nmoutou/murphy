# Critiques de qualité

Relevé du 2026-09-28. État de départ : `npm run check` vert, couverture backend 95 %
(lignes), `data/` 90 % (329 tests unitaires). Les points déjà traités auparavant ne sont
pas repris.

Classement : 🔴 critique, 🟠 important, 🟡 mineur. « Vérifié » = reproduit, pas
seulement lu dans le code.

## ✅ 1. Une trame WebSocket malformée arrête le backend — vérifié, traité

> **Traité le 2026-09-29.** `attachChatWebSocket` (`routes/chatWebSocket.ts`) : écouteur
> `error` par socket (journalisé en `warn`), `maxPayload` de 100 ko partagé avec
> `express.json()` (`utils/requestLimits.ts`), `verifyClient` sur `CORS_ORIGIN` (403),
> fermeture en `1008` après 10 s sans message. Tests : trame non masquée (rouge avant le
> correctif), message trop gros (1009), origines, inactivité.

- **Où** : `backend/src/routes/chatWebSocket.ts` (`registerChatWebSocket`),
  `backend/src/server.ts` (handler `uncaughtException`).
- **Constat** : aucun écouteur `error` sur les sockets. Dans `ws` 8.21, une trame
  invalide fait émettre `error` sur le `WebSocket` (`receiverOnError`) ; sans écouteur,
  l'`EventEmitter` la lève en `uncaughtException`, et `server.ts` y répond par
  `gracefulShutdown` → `process.exit`. Un seul client anonyme éteint le serveur.
- **Vérification** : script hors dépôt, `WebSocketServer` de `backend/node_modules/ws`,
  poignée de main à la main puis trame client non masquée (`0x81 0x02 'hi'`) →
  `UNCAUGHT: Invalid WebSocket frame: MASK must be set`.
- **Même endroit** :
  - `maxPayload` par défaut à 100 Mo (`new WebSocketServer` dans `server.ts`), contre
    100 ko pour `express.json()` ;
  - pas de contrôle d'`Origin` (`verifyClient`) : le CORS ne couvre que le HTTP,
    n'importe quel site peut ouvrir le socket et dépenser le budget de stream de l'IP ;
  - pas de délai d'inactivité : une connexion qui n'envoie jamais de message reste
    ouverte indéfiniment.
- **Piste** : `ws.on('error', …)` qui journalise et ferme ; `maxPayload` aligné sur la
  limite HTTP ; `verifyClient` sur `config.http.corsOrigins` ; délai avant le premier
  message. Test de non-régression : la trame non masquée ne doit pas lever.

## ✅ 2. JSON malformé ou corps trop gros → 500 au lieu de 400 / 413 — vérifié, traité

> **Traité le 2026-09-29.** `errorHandler` rend leur statut 4xx aux erreurs `http-errors`
> marquées `expose` (`INVALID_JSON` 400, `PAYLOAD_TOO_LARGE` 413, sinon
> `INVALID_REQUEST_BODY`), en `warn` ; une erreur interne qui porte un `status` sans
> `expose` reste un 500. `express.urlencoded()` retiré d'`app.ts` (aucune route ne lit de
> formulaire). Tests : JSON tronqué (rouge avant le correctif), corps trop gros, `status`
> sans `expose`.

- **Où** : `backend/src/middleware/errorHandler.ts` (`errorHandler`).
- **Constat** : toute erreur devient `500 INTERNAL_ERROR`, journalisée comme erreur
  serveur, y compris celles de `express.json()` (qui portent `status` / `type` :
  `entity.parse.failed`, `entity.too.large`).
- **Vérification** : test supertest jetable, `express.json()` + `errorHandler` : un
  corps `{"messages":` et un corps de 200 ko renvoient tous deux `500`.
- **Piste** : respecter le `status` 4xx des erreurs de body-parser, journalisé en `warn`.

## ✅ 3. Le frontend renvoie tout l'historique, documents intégraux compris — traité

> **Traité le 2026-09-29**, avec le point 1 (la limite de 100 ko l'exigeait) : le
> transport n'envoie que le dernier message `user`.

- **Où** : `frontend/src/lib/webSocketChatTransport.ts` (`socket.onopen`).
- **Constat** : chaque question envoie `options.messages` en entier. Le backend est
  sans état et ne lit que la dernière question, mais chaque réponse passée contient des
  parties `data-parentDocument` avec le `content` complet des documents : la requête
  grossit à chaque tour, et `parseChatRequest` valide tout avec zod. Par HTTP, la
  limite de 100 ko serait vite atteinte (voir aussi le point 2).
- **Piste** : n'envoyer que le dernier message `user`.

## ✅ 4. Qdrant sans timeout — traité

> **Traité le 2026-09-29.** `QDRANT_TIMEOUT` (ms, 10 000 par défaut, nommé comme les autres
> délais) est passé aux deux clients Qdrant : la recherche (`infra/qdrant.ts`) et la
> vérification de la collection au boot (`infra/collectionPointer.ts`, qui aurait pu
> bloquer le démarrage 300 s). L'erreur réelle est bien `QdrantClientTimeoutError`, donc
> `TIMEOUT` (sonde en Node : 53 ms pour un délai de 50). Ce n'est pas testable sous Jest :
> l'`AbortError` de `fetch` vient d'un autre realm, `instanceof Error` échoue dans le
> client et l'erreur n'est pas convertie. Les tests vérifient que le délai est transmis.

- **Où** : `backend/src/infra/qdrant.ts` (constructeur de `QdrantVectorClient`),
  `backend/src/config.ts` (`QdrantConfig`).
- **Constat** : `new QdrantClient({ url })` garde le timeout par défaut de
  `@qdrant/js-client-rest` 1.16 : 300 s. TEI et Mongo sont à 10 s, le LLM à 30 s ; le
  principe « fail fast » du backend n'est pas tenu pour la recherche.
- **Piste** : `QDRANT_TIMEOUT_MS` dans `config.ts` (et `docker-compose.base.yml`),
  passé au client ; vérifier que l'erreur produite finit en `TIMEOUT` via `toRagError`.

## ✅ 5. La configuration de production n'est pas fonctionnelle — vérifié, traité

> **Traité le 2026-09-29** (option B minimale : images et Compose corrigés, reverse proxy
> reporté au déploiement). `NEXT_PUBLIC_API_URL` est un argument de build du
> frontend ; le backend publie `5000` en prod ; les deux images de production tournent
> en `node` (`.next` copié en `--chown`, car `next start` y écrit son cache). La
> vérification a trouvé quatre autres défauts :
> - `NODE_ENV=${NODE_ENV}` (base) passait `development` depuis `.env.dev` et écrasait la
>   cible de build : retiré ;
> - la réservation GPU de TEI n'existait qu'en dev : déplacée dans base ;
> - la prod publiait le port 5001 de TEI : retiré ;
> - `mem_limit: 2g` empêchait TEI de démarrer (plus de 4 Go pendant le chargement, qui
>   dure environ 4 min) : retiré.
>
> Vérifié :
> - image construite avec une URL de test : elle est dans `.next/static`, et
>   `localhost:5000` n'y est plus ;
> - uid 1000 et `NODE_ENV=production` dans les deux conteneurs ;
> - stack de prod : santé `ok`, question par WebSocket jusqu'au `finish` (5 documents,
>   5 passages), page frontend en 200.
>
> Documenté dans `docs/technical/ARCHITECTURE.md` (§ Production).

- **Où** : `frontend/Dockerfile`, `docker-compose.prod.yml`, `backend/Dockerfile`.
- **Constat** :
  - `NEXT_PUBLIC_API_URL` n'est pas un `ARG` du stage `builder` : `next build` l'inline
    comme absent, le bundle client vise toujours `http://localhost:5000`. La variable
    passée par Compose à l'exécution n'a aucun effet côté navigateur ;
  - en prod, aucun port n'est publié pour le backend : le navigateur ne peut pas le
    joindre sans proxy ;
  - les images de production tournent en `root` (pas de `USER node`).
- **Piste** : si c'est assumé tant que rien n'est déployé, l'écrire ; sinon
  `ARG`/`ENV` au build, proxy ou port publié, `USER node`.

## ✅ 6. `CLAUDE.md` décrit un dépôt qui n'existe plus — traité

> **Traité le 2026-09-29**, et étendu à toute la documentation :
> - `CLAUDE.md` suit l'arborescence réelle ; la recopie des règles globales en est retirée ;
> - les ADR des volets Évaluation et Ontologie sont supprimés, les autres perdent leurs
>   renvois morts (tickets, exigences, documents absents) ; l'INDEX est réécrit ;
> - les liens des docs techniques et des README visent `docs/technical/` ;
> - les identifiants de tickets sont retirés des commentaires du code ;
> - la partition de configuration vide `data/conf/base/evaluation/` est supprimée.

- **Constat** : il cite `eval/`, `docs/product/` (ADR compris) et `data/docs/`, absents.
  Les ADR sont dans `docs/pilotage/ADR/`, la documentation des projets dans
  `docs/technical/{backend,data,frontend}/`. Ce fichier est relu à chaque session : un
  écart y induit en erreur.
- **Piste** : aligner la section « Repository layout » et les renvois sur l'arborescence.

## ✅ 7. Réponse tronquée non signalée — traité

> **Traité le 2026-09-29**, autrement que la piste : la limite est supprimée plutôt que
> signalée. `LLM_MAX_TOKENS` disparaît (`config.ts`, `docker-compose.base.yml`,
> `.env.example`) et la requête au LLM (`infra/llm.ts`) ne porte plus de `max_tokens` :
> la réponse a la longueur que le modèle produit. Seul le plafond du fournisseur (en
> général la fenêtre de contexte) peut encore couper, et `finishReason: 'stop'` redevient
> juste. Test : le corps envoyé au LLM ne contient aucune limite.

- **Où** : `backend/src/infra/llm.ts` (`extractToken`), `services/chatService.ts`
  (`writeFinish`).
- **Constat** : un arrêt sur `max_tokens` (`finish_reason: 'length'`) est ignoré ; le
  backend envoie `finishReason: 'stop'`. Une réponse juridique coupée en silence passe
  pour complète.
- **Piste** : remonter la raison de fin jusqu'à la partie `finish`, et l'afficher.

## 🟡 8. Écarts de style avec les règles du `CLAUDE.md`

- `infra/llm.ts`, `infra/embedding.ts`, `infra/qdrant.ts`, `infra/mongodb.ts`
  utilisent le logger racine au lieu d'un `rootLogger.child({ context })`.
- Déclarations `function` au lieu de fonctions fléchées : `routes/health.ts`,
  `services/ragService.ts`, `infra/collectionPointer.ts`, `utils/response.ts`,
  `utils/configWarnings.ts`.
- `routes/chat.ts` : la réponse d'erreur 500 est écrite trois fois.
- `services/ragService.ts` : `buildContextString` renvoie une phrase anglaise (« No relevant
  documents found. ») dans un prompt système français.

## 🟡 9. `forceExit` masque des handles ouverts dans les tests backend

- **Où** : `backend/jest.config.js` (`forceExit: true`, `detectOpenHandles: false`).
- **Constat** : chaque `npm test` affiche « Force exiting Jest ». Un timer ou une
  connexion non fermée dans un test passe inaperçu.
- **Piste** : un passage avec `--detectOpenHandles`, fermer ce qui reste, retirer
  `forceExit`.
