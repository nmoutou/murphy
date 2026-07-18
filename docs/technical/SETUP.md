# Setup & Configuration — Murphy

## Prérequis

- **Docker & Docker Compose**
- **Node.js** 20+ (backend) / 22+ (frontend) si exécution locale
- **GPU NVIDIA** pour le service d'embedding TEI (déclaré dans `docker-compose.dev.yml`).
  Sans GPU, lancez backend/frontend en local et pointez les variables vers des services
  accessibles.
- Bases de données **pré-peuplées** (MongoDB + Qdrant). L'ingestion LEGIFRANCE ne fait pas
  partie de ce dépôt.

## Stack complète (Docker Compose)

Les scripts racine enveloppent Docker Compose et requièrent un fichier **`.env.dev`** à la
racine (gitignoré — à créer avant tout démarrage).

```bash
npm run up        # build + démarre la stack dev, détaché (base + dev overrides)
npm run watch     # idem, au premier plan (streame les logs)
npm run logs      # suivre les logs
npm run status    # tableau de statut des conteneurs
npm run ps        # statut (compose ps)
npm run down      # tout arrêter (inclut l'override prod)
npm run restart   # redémarrer
npm run build     # docker compose build
```

Ces scripts utilisent `docker-compose.base.yml` + `docker-compose.dev.yml` avec
`--env-file .env.dev`.

### Ports (dev)

| Service | Port hôte → conteneur |
|---------|-----------------------|
| Frontend | `3000` |
| Backend | `5000` |
| Qdrant | `6333` |
| MongoDB | `27017` |
| Neo4j | `7474` (HTTP) / `7687` (Bolt) |
| Service d'embedding (TEI) | `5001 → 80` |

En dev, les sources sont montées dans les conteneurs avec hot-reload
(`npm run dev:watch` pour le backend, `next dev` pour le frontend).

## Backend sans Docker

Depuis `backend/` :

```bash
npm run dev          # ts-node src/server.ts
npm run dev:watch    # nodemon + ts-node (auto-restart)
npm run build        # tsc -> dist/
npm run type-check   # tsc --noEmit
npm run lint         # eslint src
npm test             # jest
npm run test:watch
npx jest path/to/file.test.ts     # un fichier de test
npx jest -t "nom du test"         # tests par nom
```

Jest impose des seuils de couverture (`jest.config.js` : lines/statements 65 %,
functions 60 %, branches 40 %). `src/server.ts` est exclu de la couverture.

## Frontend sans Docker

Depuis `frontend/` : `npm run dev` (Turbopack), `npm run build`, `npm run lint`.
Alias de chemin TS : `@/*` → `frontend/src/*`.

## Variables d'environnement

Toute la configuration runtime est pilotée par l'environnement. La liste passée au backend
en Docker se trouve dans le bloc `environment:` de `docker-compose.base.yml`.
`backend/src/utils/configWarnings.ts:checkEnvironment()` s'exécute au démarrage et avertit
des variables manquantes/suspectes — c'est la **liste de référence** faisant autorité.

### Critiques (le backend log une erreur si absentes)

| Variable | Rôle |
|----------|------|
| `LLM_API_ENDPOINT` | URL de l'API LLM (OpenAI-compatible) |
| `LLM_API_KEY` | Clé d'API LLM |
| `LLM_MODEL` | Modèle LLM |
| `MONGODB_URI` | Connexion MongoDB |

### Optionnelles (fallback si absentes)

| Variable | Défaut | Rôle |
|----------|--------|------|
| `PORT` | `5000` | Port du backend |
| `NODE_ENV` | `development` | Environnement |
| `LOG_LEVEL` | `info` | Niveau de log Pino |
| `CORS_ORIGIN` | — | Origine(s) CORS autorisée(s) |
| `RATE_LIMIT_WINDOW_MS` / `RATE_LIMIT_MAX` | — | Rate limit global |
| `STREAM_RATE_LIMIT_WINDOW_MS` / `STREAM_RATE_LIMIT_MAX` | — | Rate limit du stream chat |
| `MONGODB_DATABASE` | — | Base MongoDB |
| `MONGODB_COLLECTION` | `chunks` | Collection des chunks |
| `MONGODB_TIMEOUT` | — | Timeout MongoDB |
| `EMBEDDING_SERVICE_URL` | `http://embedding-service:80` | URL du service TEI |
| `EMBEDDING_MODEL_NAME` | `all-mpnet-base-v2` | Nom du modèle d'embedding |
| `EMBEDDING_SERVICE_TIMEOUT` | `10000` (ms) | Timeout embedding |
| `QDRANT_URL` | `http://qdrant:6333` | URL de Qdrant |
| `QDRANT_COLLECTION` | `chunks` | Collection Qdrant |
| `RETRIEVAL_TOP_K` | `5` | Nombre de chunks récupérés |
| `RETRIEVAL_MIN_SCORE` | `0.5` | Seuil de score Qdrant |
| `LLM_TEMPERATURE` | `0.7` | Température LLM |
| `LLM_MAX_TOKENS` | `1000` | Tokens max de la réponse |
| `LLM_TIMEOUT` | `30000` (ms) | Timeout LLM |
| `SYSTEM_PROMPT` | prompt juridique FR par défaut | Surcharge du system prompt |

> Le service d'embedding (image TEI) lit `EMBEDDING_MODEL` (l'id de modèle HuggingFace
> passé en `--model-id`) côté Docker Compose, distinct de `EMBEDDING_MODEL_NAME` lu par le
> client backend.

Le frontend lit `NEXT_PUBLIC_API_URL` et `NEXT_PUBLIC_WS_URL`
(défaut WS : `ws://localhost:5000/api/v1/chat/ws`).

## Vérifier la santé

```bash
curl http://localhost:5000/api/v1/health
```

Réponse `ok` (200) si TEI + Qdrant + MongoDB répondent ; `degraded`/`down` et `503` sinon.
`/api/v1/health/services` ajoute la latence mesurée par service.

## Accès aux bases

```bash
# Qdrant — dashboard
http://localhost:6333/dashboard

# Neo4j — browser
http://localhost:7474

# Test d'embedding (TEI)
curl -X POST http://localhost:5001/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{ "model": "all-mpnet-base-v2", "input": ["Texte de test"] }'
```

## Troubleshooting

- **Qdrant vide** → le retrieval renvoie 0 source. Les bases doivent être pré-peuplées
  (ingestion hors dépôt).
- **Embedding indisponible** → vérifier le GPU NVIDIA et le conteneur `embedding-service`
  (`npm run logs`). Sans GPU, ce service ne démarrera pas.
- **LLM timeout / 4xx** → vérifier `LLM_API_ENDPOINT`, `LLM_API_KEY`, `LLM_MODEL` ; augmenter
  `LLM_TIMEOUT` si le réseau est lent.
- **`.env.dev` manquant** → les scripts `npm run *` échouent ; créez-le d'abord.
