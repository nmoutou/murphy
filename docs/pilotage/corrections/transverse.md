# Corrections transverses

> Défauts qui traversent plusieurs dépôts : le code de chaque dépôt
> peut être correct pris isolément, c'est leur jointure qui est fausse.
> Index et ordre d'exécution : [`README.md`](README.md).

| ID | Point | Sévérité | Statut |
|---|---|---|---|
| TR-01 | **Contrat serving ↔ ingestion rompu** (§1) | Bloquant | 🔶 [ADR-039](../../product/ADR/ADR-039-contrat-ingestion-serving.md) accepté · côté `data/` fait, backend à suivre |
| TR-02 | L'URL WebSocket configurée n'a pas de chemin : le serveur refuse la connexion (§2) | Bloquant | ⬜ |
| TR-03 | La prod ne peut pas joindre le backend depuis le navigateur (§3) | Dette | ⏸ décision de déploiement |
| TR-04 | `types/messages.ts` est dupliqué entre backend et frontend, sans contrôle | Confort | ⬜ |
| TR-05 | `CLAUDE.md` décrit un état qui n'est plus vrai (§4) | Dette | ⬜ après les lots |
| TR-06 | Environnement local : `node_modules` appartenant à root, `eval/` ne s'installe pas (§5) | Dette | ⬜ |

## 1. TR-01 — contrat serving ↔ ingestion

**Décision** : [ADR-039](../../product/ADR/ADR-039-contrat-ingestion-serving.md),
option (b). Le payload porte `char_start`/`char_end`, le texte est découpé
dans le `content` du document Mongo, et le pointeur publié porte une
version du contrat, vérifiée au boot. Le flux envoie au client chaque
document parent une fois (`data-parentDocument`, texte entier) et chaque
passage avec ses bornes de surlignage (`data-document`).

**Côté `data/` : fait.** Le payload porte `char_start`/`char_end`, le
pointeur `serving_contract_version` (`SERVING_CONTRACT_VERSION` = 1),
et un run restreint ne publie que sur un pointeur de même version
(`may_publish`). Reste le backend (lot 4) et l'alignement du type côté
frontend (TR-04).

**Constat confirmé le 25 septembre 2026** sur la collection publiée
`9424808d…` : le payload montre `chunk_id` et aucun `chunkId`, ni texte,
ni `title`. `LEGIFRANCE` ne contient que `documents` et `manifest`.

| | L'ingestion écrit (`data/src/ragcore`) | Le backend lit (`backend/src`) |
|---|---|---|
| Payload Qdrant | `chunk_id`, `identifier`, `owner_id` + les métadonnées du document (`adapters/storage/qdrant/vector_repository.py:66`) | `payload.chunkId`, `payload.title`, `payload.type` (`services/chatService.ts:59-65`) |
| Collection Mongo | `documents` : un document **entier** par `identifier` (`adapters/storage/mongo/document_repository.py:27`) | `MONGODB_COLLECTION` = `chunks`, requêtée par `chunkId` (`infra/mongodb.ts:98-101`) |
| Texte du chunk | jamais persisté tel quel : ni `text` ni `char_start`/`char_end` dans le payload | attendu dans `content` |

Le champ `chunkId` n'existe plus que dans le code mort
`data/src/data/models/data.py:63` (DA-01) : c'est le vestige de l'ancien
contrat.

**Conséquence attendue.** La garde `if (result.payload?.chunkId)` écarte
tous les résultats Qdrant :
- aucune source n'est envoyée au client ;
- `fetchChunkDocuments` reçoit une liste vide ;
- le LLM répond avec le contexte `No relevant documents found.`

La réponse s'affiche donc, mais sans jamais s'appuyer sur le corpus.

**Décision à prendre (ADR)** : où vit le texte d'un chunk.
- (a) Ajouter `text` au payload Qdrant. Le backend n'a plus besoin de
  Mongo pour le contexte, ce qui retire une étape (`docFetchMs`) du
  pipeline. En contrepartie, le texte est stocké deux fois (Mongo
  `content` + Qdrant). ~~Le fingerprint de collection change~~ : faux, il
  ne dépend que de `WorkflowConfig`. Les trois options imposent une
  réingestion, dans la même collection.
- (b) Ajouter `char_start`/`char_end` au payload, puis découper le
  `content` du document Mongo lu par `identifier`. Rien n'est dupliqué,
  mais le backend lit des documents entiers pour en extraire quelques
  centaines de caractères.
- (c) Ajouter une collection Mongo `chunks`. Le texte est aussi stocké
  deux fois, et on ajoute une écriture à la saga.

**Ce qui suit l'ADR** : le type `DocumentChunk` (backend + frontend),
`chatService`, `ragService`, `infra/mongodb.ts`, la section « RAG
request flow » de `CLAUDE.md` et `backend/docs/ARCHITECTURE.md`. Le
titre d'une source vient aujourd'hui de `payload.title`, que l'ingestion
n'écrit pas non plus.

### Vérification préalable

```bash
curl -s localhost:6333/collections/<collection publiée>/points/scroll \
  -H 'content-type: application/json' -d '{"limit":1,"with_payload":true}'
```

Le point doit montrer `chunk_id` et aucun `chunkId`. Si c'est le cas,
TR-01 est confirmé.

## 2. TR-02 — URL WebSocket sans chemin

`.env.example:70` et le `.env.dev` local déclarent
`NEXT_PUBLIC_WS_URL=ws://localhost:5000`. Le frontend passe cette valeur
**telle quelle** à `new WebSocket(...)` (`frontend/src/hooks/useRagChat.ts:65`).
Le repli `ws://localhost:5000/api/v1/chat/ws`, lui, est correct, mais il
ne sert que si la variable est absente.

Le serveur WebSocket est monté avec `path: '/api/v1/chat/ws'`
(`backend/src/server.ts:18`), et la bibliothèque `ws` refuse en 400 toute
mise à niveau vers un autre chemin.

**Correction** : une seule variable de base, `NEXT_PUBLIC_API_URL`, dont
le frontend dérive le chemin. `NEXT_PUBLIC_API_URL` n'est aujourd'hui lue
que par du code mort (FE-04). Supprimer `NEXT_PUBLIC_WS_URL` de
`.env.example` et de `docker-compose.base.yml:87`.

## 3. TR-03 — la prod ne joint pas le backend

- Dans `docker-compose.prod.yml`, le backend ne publie **aucun port**, et
  aucun reverse proxy n'est déclaré. Or c'est le **navigateur** qui ouvre
  le WebSocket vers le backend.
- Next.js **inline les `NEXT_PUBLIC_*` au build**. Les passer via
  `environment:` (`docker-compose.base.yml:86-87`) n'agit qu'en mode
  `next dev`. L'image de production, construite sans ces variables, retombe
  sur `ws://localhost:5000/...`.

**Décision à prendre** : servir le frontend et l'API sous la même origine
derrière un reverse proxy (`/api` → backend). L'URL devient alors
relative, TR-02 disparaît, et `trust proxy` (BE-03) prend une valeur
connue. Sinon, passer les URL en `ARG` de build dans
`frontend/Dockerfile`.

## 4. TR-05 — `CLAUDE.md` à réaligner

À corriger une fois les lots faits, pour ne le réécrire qu'une fois :
- le flux RAG décrit « par `chunkId` » (TR-01) ;
- les singletons « lazy via `Proxy` » du barrel `infra/index.ts` (BE-06) ;
- la variable citée `EMBEDDING_MODEL` : le backend lit
  `EMBEDDING_MODEL_NAME` (`infra/embedding.ts:31`), que compose alimente
  depuis `EMBEDDING_MODEL` ;
- le dossier `eval/` à la racine n'est pas mentionné dans « Repository
  layout ».

## 5. TR-06 — environnement local

- `backend/node_modules` et `frontend/node_modules` sont des **dossiers
  vides appartenant à root**, créés par les volumes anonymes de
  `docker-compose.dev.yml`. `npm ci` échoue en `EACCES`, et donc aussi
  `npm run lint`, `npm test` et `tsc` hors Docker. Pour débloquer :
  `sudo rm -rf backend/node_modules frontend/node_modules`, puis `npm ci`
  dans chacun des deux dossiers.
- `eval/` : `uv sync` échoue. `pyyaml` (tiré par `ranx` → `ir-datasets`)
  se compile depuis les sources et réclame Cython, ce qui suggère qu'aucune
  wheel binaire n'existe pour la version de Python résolue. À investiguer :
  épingler une version de Python, ou de `pyyaml`, qui dispose d'une wheel.
