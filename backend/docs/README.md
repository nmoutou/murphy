# Documentation — murphy-backend

Documentation technique du backend de **serving** de Murphy : l'API Express/TypeScript qui
orchestre le pipeline RAG à la requête (embed → retrieve → fetch → stream LLM).

## Quoi lire, dans quel ordre

| Document | Contenu |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Vue d'ensemble : le pipeline RAG, les trois transports, les clients d'infrastructure, les conventions transverses. **Commencer ici.** |
| `reference/` | Références détaillées (contrat de messages, API, configuration) — *à écrire ; même ossature que `data/docs/reference/`.* |

La vue système globale (serving + ingestion + bases partagées) vit dans le repo parent :
`docs/technical/ARCHITECTURE.md`.

---

## Opérations

### Avec Docker (stack complète)

Depuis la **racine du repo parent** (requiert `.env.dev`, gitignoré) :

```bash
npm run up        # build + démarre la stack dev (backend inclus), détaché
npm run watch     # idem, au premier plan
npm run logs      # suivre les logs
npm run down      # tout arrêter
```

Le backend écoute sur le port `5000` en dev, sources montées avec hot-reload.

### Sans Docker

Aucun fichier d'environnement n'est chargé : exporter les variables avant (par exemple
`set -a; . ../.env.dev; set +a`, puis surcharger les noms d'hôtes Docker comme
`QDRANT_URL`). Depuis `backend/` :

```bash
npm run dev          # ts-node src/server.ts
npm run dev:watch    # nodemon + ts-node (auto-restart)
npm run build        # tsc -> dist/
npm run type-check   # tsc --noEmit
npm run lint         # eslint src
npm test             # jest (ne mesure pas la couverture)
npx jest --coverage  # vérifie les seuils : lines/statements 65 %, functions 60 %, branches 40 %
npx jest chemin/du/fichier.test.ts    # un fichier
npx jest -t "nom du test"             # par nom
```

### Configuration

Tout est piloté par variables d'environnement (en Docker : bloc `environment:` de
`docker-compose.base.yml`, alimenté par le `.env.dev` racine). **`src/config.ts` est la
référence** : il lit et valide l'environnement une fois au démarrage, avec ses valeurs
par défaut, et c'est le seul fichier qui lit `process.env`. Une valeur vide vaut une
variable absente. Un nombre invalide (`LLM_TEMPERATURE=abc`) **bloque le démarrage**,
avec un message qui nomme la variable. `checkEnvironment` journalise ensuite les
variables manquantes et celles qui ont pris leur valeur par défaut.

Critiques (erreur logguée si absentes, sans bloquer) : `LLM_API_ENDPOINT`, `LLM_API_KEY`, `LLM_MODEL`,
`MONGODB_URI`. Principales optionnelles : `PORT` (5000), `MONGODB_DATABASE`/`COLLECTION`,
`MONGODB_META_DB_NAME` (MURPHY_META — le pointeur de collection), `QDRANT_URL`,
`QDRANT_COLLECTION` (repli seulement — voir ARCHITECTURE), `EMBEDDING_SERVICE_URL`,
`EMBEDDING_MODEL_NAME`, `RETRIEVAL_TOP_K` (5), `RETRIEVAL_MIN_SCORE` (0.5),
`LLM_TEMPERATURE`/`MAX_TOKENS`/`TIMEOUT`, `SYSTEM_PROMPT`, les rate limits et
`CORS_ORIGIN`.

### Santé

```bash
curl http://localhost:5000/api/v1/health   # ok | degraded (1 service down) | down (2+), 503 si non-ok, latence par service
                                            # (/api/v1/health/services en est un alias)
```

### Diagnostic rapide

| Symptôme | Piste |
|---|---|
| Refus de démarrer : « collection Qdrant n'existe pas » | Aucun run d'ingestion `ok` n'a publié de pointeur, et le repli `QDRANT_COLLECTION` pointe sur rien. Lancer une ingestion complète (`kedro run` dans `data/`). |
| 0 source sur toutes les questions | Collection vide, ou `RETRIEVAL_MIN_SCORE` trop haut. |
| Embedding indisponible | Conteneur TEI (GPU requis) — `npm run logs` depuis la racine. |
| LLM timeout / 4xx | `LLM_API_ENDPOINT` / `LLM_API_KEY` / `LLM_MODEL` ; augmenter `LLM_TIMEOUT` si réseau lent. |
