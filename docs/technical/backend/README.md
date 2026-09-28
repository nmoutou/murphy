# Documentation — backend

Documentation technique du backend de **serving** de Murphy : l'API Express/TypeScript qui
orchestre le pipeline RAG à la requête (embed → retrieve → fetch → stream LLM).

## Quoi lire, dans quel ordre

| Document | Contenu |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Vue d'ensemble : le pipeline RAG, les trois transports, les clients d'infrastructure, les conventions transverses. **Commencer ici.** |
| `reference/` | Références détaillées (contrat de messages, API, configuration) — *à écrire ; même ossature que `data/docs/reference/`.* |

La vue système globale (serving + ingestion + bases partagées) vit à la racine du dépôt :
[`docs/technical/ARCHITECTURE.md`](../../docs/technical/ARCHITECTURE.md).

---

## Opérations

### Avec Docker (stack complète)

Depuis la **racine du dépôt** (requiert `.env.dev`, gitignoré) :

```bash
npm run up        # build + démarre la stack dev (backend inclus), détaché
npm run watch     # idem, au premier plan
npm run logs      # suivre les logs
npm run down      # tout arrêter
```

Le backend écoute sur le port `5000` en dev. Seul `src/` est monté, avec hot-reload :
les dépendances et le contrat compilé vivent dans l'image, donc changer
`package.json`, `tsconfig.json` ou `packages/contract` demande `npm run serve:build`.

### Sans Docker

Aucun fichier d'environnement n'est chargé : exporter les variables avant (par exemple
`set -a; . ../.env.dev; set +a`, puis surcharger les noms d'hôtes Docker comme
`QDRANT_URL`). Installer une fois **depuis la racine** : `npm install` (un seul lockfile
pour les workspaces ; le `postinstall` construit `packages/contract`). `npm run check` à
la racine lance tout ce que lance la CI. Puis, depuis `backend/` :

```bash
npm run dev          # ts-node src/server.ts
npm run dev:watch    # nodemon + ts-node (auto-restart)
npm run build        # tsc -> dist/
npm run type-check   # tsc --noEmit
npm run lint         # eslint src (règles de taille : voir ci-dessous)
npm test             # jest (ne mesure pas la couverture)
npx jest --coverage  # vérifie les seuils : lines/statements 65 %, functions 60 %, branches 40 %
npx jest chemin/du/fichier.test.ts    # un fichier
npx jest -t "nom du test"             # par nom
```

Le lint (`eslint.config.mjs`) vérifie les limites du CLAUDE.md : 300 lignes par fichier,
30 lignes par fonction (hors lignes vides et commentaires), imbrication 3, 4 paramètres,
complexité 10, pas de nombre magique. Les tests (`src/__tests__/`) sont exemptés des
règles de longueur de fonction et de nombres magiques. Les codes HTTP sont nommés une fois,
dans `utils/httpStatus.ts`.

### Configuration

Tout est piloté par variables d'environnement (en Docker : bloc `environment:` de
`docker-compose.base.yml`, alimenté par le `.env.dev` racine). **`src/config.ts` est la
référence** : il lit et valide l'environnement une fois au démarrage, avec ses valeurs
par défaut, et c'est le seul fichier qui lit `process.env`. Une valeur vide vaut une
variable absente. Un nombre invalide (`LLM_TEMPERATURE=abc`) **bloque le démarrage**,
avec un message qui nomme la variable. `checkEnvironment` journalise ensuite les
variables manquantes et celles qui ont pris leur valeur par défaut.

Critiques (erreur logguée si absentes, sans bloquer) : `LLM_API_ENDPOINT`, `LLM_API_KEY`, `LLM_MODEL`,
`MONGODB_URI`. Principales optionnelles : `PORT` (5000), `MONGODB_DATABASE` (LEGIFRANCE),
`MONGODB_META_DB_NAME` (MURPHY_META — le pointeur de collection), `QDRANT_URL`,
`EMBEDDING_SERVICE_URL`, `EMBEDDING_MODEL_NAME`, `RETRIEVAL_TOP_K` (5), `RETRIEVAL_MIN_SCORE` (0.5),
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
| Refus de démarrer : « Aucun run d'ingestion n'a publié de collection » ou « collection Qdrant n'existe pas » | Pas de pointeur, ou il désigne une collection disparue. Lancer un run complet : `kedro run --params source=all` dans `data/`. |
| Refus de démarrer : « contrat de serving vN » | Le corpus publié et le backend ne suivent pas la même version du contrat (ADR-039). Version plus ancienne ou absente : réingérer (run complet). Plus récente : mettre à jour le backend. |
| Part `error` « Serving contract violated » | Un point Qdrant, son document Mongo ou ses offsets ne respectent pas le contrat ; le message cite le `chunk_id`. Réingérer le corpus. |
| 0 source sur toutes les questions | Collection vide, ou `RETRIEVAL_MIN_SCORE` trop haut. |
| Embedding indisponible | Conteneur TEI (GPU requis) — `npm run logs` depuis la racine. |
| LLM timeout / 4xx | `LLM_API_ENDPOINT` / `LLM_API_KEY` / `LLM_MODEL` ; augmenter `LLM_TIMEOUT` si réseau lent. |
