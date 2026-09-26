# Corrections transverses

> Défauts qui traversent plusieurs projets : le code de chaque projet
> peut être correct pris isolément, c'est leur jointure qui est fausse.
> Index et ordre d'exécution : [`README.md`](README.md).

| ID | Point | Sévérité | Statut |
|---|---|---|---|
| TR-01 | **Contrat serving ↔ ingestion rompu** (§1) | Bloquant | ✅ [ADR-039](../../product/ADR/ADR-039-contrat-ingestion-serving.md) · `data/`, backend et frontend (TR-04) |
| TR-02 | L'URL WebSocket configurée n'a pas de chemin : le serveur refuse la connexion (§2) | Bloquant | ✅ `lib/chatSocketUrl.ts` |
| TR-03 | La prod ne peut pas joindre le backend depuis le navigateur (§3) | Dette | ⏸ décision de déploiement |
| TR-04 | `types/messages.ts` est dupliqué entre backend et frontend, sans contrôle (§6) | Confort | ✅ `packages/contract` ([ADR-040](../../product/ADR/ADR-040-depot-unique.md)) |
| TR-05 | `CLAUDE.md` décrit un état qui n'est plus vrai (§4) | Dette | ✅ |
| TR-06 | Environnement local : `node_modules` appartenant à root, `eval/` ne s'installe pas (§5) | Dette | 🔶 `node_modules` réglé (ADR-040), reste `eval/` |
| TR-07 | Sous-modules : un changement de contrat traverse trois ou quatre dépôts (§6) | Dette | ✅ [ADR-040](../../product/ADR/ADR-040-depot-unique.md) |

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
(`may_publish`).

**Côté backend : fait (lot 4).** Le boot refuse un pointeur absent ou
d'une autre version, sans repli (`MONGODB_COLLECTION` et
`QDRANT_COLLECTION` retirés). Le payload est validé à la lecture ; les
documents parents sont lus par `(identifier, owner_id)` et chaque passage
découpé en points de code (`services/passages.ts`). Le flux envoie
`data-parentDocument` une fois par document, puis `data-document` avec
les bornes de surlignage en UTF-16 ; le LLM ne reçoit que les passages.
Vérifié sur la stack de dev : 4 documents, 5 passages, bornes justes.

**Côté frontend : fait (TR-04).** Le type vient du contrat partagé
(`@murphy/contract/messages`), et `useChat` valide les parts à l'arrivée.
L'UI lit toujours les seules parts `data-document` ; l'affichage du
document parent et du surlignage est un futur lot frontend.

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

**Fait (26 septembre 2026).** `frontend/src/lib/chatSocketUrl.ts` déduit
l'adresse de `NEXT_PUBLIC_API_URL` (défaut `http://localhost:5000`) :
`http:` → `ws:`, `https:` → `wss:`, chemin `/api/v1/chat/ws`. Une URL
malformée lève une erreur qui nomme la variable. `NEXT_PUBLIC_WS_URL`
est retirée de `.env.example`, de compose et du `.env.dev` local.
Vérifié sur la stack de dev : la valeur est bien inlinée dans le bundle
servi, et un WebSocket ouvert sur l'adresse déduite reçoit 5
`data-parentDocument` et 5 `data-document`. Dans le navigateur, une
question affiche ses sources ; la réponse du LLM manque, faute de
variables LLM dans le `.env.dev` local, et l'échec ne s'affiche pas
(FE-03). La prod reste soumise à TR-03 : l'image est construite sans la
variable.

## 3. TR-03 — la prod ne joint pas le backend

- Dans `docker-compose.prod.yml`, le backend ne publie **aucun port**, et
  aucun reverse proxy n'est déclaré. Or c'est le **navigateur** qui ouvre
  le WebSocket vers le backend.
- Next.js **inline les `NEXT_PUBLIC_*` au build**. Passer
  `NEXT_PUBLIC_API_URL` via `environment:` (`docker-compose.base.yml:84`)
  n'agit qu'en mode `next dev`. L'image de production, construite sans
  cette variable, retombe sur `ws://localhost:5000/api/v1/chat/ws`.

**Décision à prendre** : servir le frontend et l'API sous la même origine
derrière un reverse proxy (`/api` → backend). L'URL devient alors
relative : `chatSocketUrl.ts` devra la déduire de l'origine de la page,
et `trust proxy` (BE-03) prend une valeur connue. Sinon, passer
`NEXT_PUBLIC_API_URL` en `ARG` de build dans `frontend/Dockerfile`.

## 4. TR-05 — `CLAUDE.md` à réaligner

À corriger une fois les lots faits, pour ne le réécrire qu'une fois :
- le flux RAG décrit « par `chunkId` » (TR-01) ;
- les singletons « lazy via `Proxy` » du barrel `infra/index.ts` (BE-06) ;
- la variable citée `EMBEDDING_MODEL` : le backend lit
  `EMBEDDING_MODEL_NAME` (`infra/embedding.ts:31`), que compose alimente
  depuis `EMBEDDING_MODEL` ;
- le dossier `eval/` à la racine n'est pas mentionné dans « Repository
  layout ».

**Fait (26 septembre 2026)** : les quatre points étaient déjà réglés au fil
des lots. La relecture contre le code en a trouvé d'autres, corrigés :
- les paramètres de `data/` vivent dans `conf/base/workflow/` (ADR-026) ;
- l'alias du health est `/api/v1/health/services` ;
- `neo4j` n'a pas de profil Compose ;
- seul `data/docs/` a un dossier `reference/`.

La partie projet est aussi resserrée, et les doublons entre sections sont
supprimés (pointeur de collection, fichier d'env). La partie règles est
gardée telle quelle, exemples compris (décision du porteur). Le fichier
passe de 490 à 458 lignes.

## 5. TR-06 — environnement local

- ✅ *Réglé par ADR-040* : `docker-compose.dev.yml` ne monte plus que les
  sources, sans volume `node_modules`, et l'installation se fait une fois
  à la racine (`npm install`). Constat d'origine :
  `backend/node_modules` et `frontend/node_modules` étaient des **dossiers
  vides appartenant à root**, créés par les volumes anonymes de
  `docker-compose.dev.yml`. `npm ci` échoue en `EACCES`, et donc aussi
  `npm run lint`, `npm test` et `tsc` hors Docker. Pour débloquer :
  `sudo rm -rf backend/node_modules frontend/node_modules`, puis `npm ci`
  dans chacun des deux dossiers.
- `eval/` : `uv sync` échoue. `pyyaml` (tiré par `ranx` → `ir-datasets`)
  se compile depuis les sources et réclame Cython, ce qui suggère qu'aucune
  wheel binaire n'existe pour la version de Python résolue. À investiguer :
  épingler une version de Python, ou de `pyyaml`, qui dispose d'une wheel.

## 6. TR-04 et TR-07 — un seul dépôt, un contrat partagé

**Décision** : [ADR-040](../../product/ADR/ADR-040-depot-unique.md). Les
sous-modules sont réintégrés avec leur historique (4 commits : un retrait,
trois fusions), sans changer d'emplacement. Backend, frontend et
`packages/contract` sont des npm workspaces, avec un seul lockfile.

- **Le contrat** : `@murphy/contract/messages`, des schémas zod et les
  types qui en sont déduits. Les deux copies de `types/messages.ts` sont
  supprimées. Vérifié : renommer un champ du schéma casse le `tsc` des
  deux côtés.
- **FE-01** fait au passage : le `tsc` du frontend est vert.
- **Docker** : le contexte de build est la racine, avec un
  `.dockerignore` qui exclut `.env*` (vérifié : aucun `.env` dans les
  images). En dev, seules les sources sont montées.
- **CI** : une seule, à la racine (`npm run check`, puis le build des deux
  images en production). Le lint du frontend y entrera avec FE-02.
- **Versions** : le lockfile unique garde, pour chaque dépendance
  directe, la version exacte des anciens lockfiles. Une résolution
  fraîche avait tiré `@qdrant/qdrant-js` 1.19, qui a retiré `search`.
  Il reste trois copies de `ai` 6.0.291, toutes de la même version :
  dédoublonner aurait changé des dizaines de dépendances transitives.
