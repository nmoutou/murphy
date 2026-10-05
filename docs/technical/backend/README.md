# Documentation — backend

Documentation technique du backend de **serving** de Murphy : l'API Express/TypeScript qui
orchestre le pipeline RAG à la requête (embed → recherche hybride → fetch → stream LLM).

## Quoi lire, dans quel ordre

| Document | Contenu |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Vue d'ensemble : le pipeline RAG, les trois transports, les clients d'infrastructure, les conventions transverses. **Commencer ici.** |
| `reference/` | Références détaillées (contrat de messages, API, configuration) — *à écrire ; même ossature que [`data/reference/`](../data/reference/).* |

La vue système globale (serving + ingestion + bases partagées) est dans
[`docs/technical/ARCHITECTURE.md`](../ARCHITECTURE.md).

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
`package.json`, `tsconfig.json` ou `packages/contract` demande `npm run build` puis `npm run up`.

### Sans Docker

Aucun fichier d'environnement n'est chargé : exporter les variables avant (par exemple
`set -a; . ../.env.dev; set +a`, puis surcharger les noms d'hôtes Docker comme
`EMBEDDING_SERVICE_URL`). Installer une fois **depuis la racine** : `npm install` (un seul lockfile
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
avec un message qui nomme la variable, comme une pagination incohérente : `PAGINATION_SIZE`
et `PAGINATION_DEPTH` doivent être des entiers positifs, avec une profondeur entre la
taille et 10 000 (le plafond du `k` d'un kNN). `checkEnvironment` journalise ensuite les
variables manquantes et celles qui ont pris leur valeur par défaut.

Critiques (erreur logguée si absentes, sans bloquer) : `LLM_API_ENDPOINT`, `LLM_API_KEY`, `LLM_MODEL`,
`MONGODB_URI`, `OPENSEARCH_INDEX` (le nom de l'index, partagé avec l'ingestion).
Principales optionnelles : `PORT` (5000), `NODE_LOG_LEVEL` (`debug` en dev, `info` en prod),
`MONGODB_DATABASE` (MURPHY_DATA),
`OPENSEARCH_URL`, `OPENSEARCH_TIMEOUT` (10000 ms), `PAGINATION_SIZE` (10), `PAGINATION_DEPTH` (100),
`EMBEDDING_SERVICE_URL`, `EMBEDDING_MODEL_NAME`,
`LLM_TEMPERATURE`/`TIMEOUT`, `SYSTEM_PROMPT`, les rate limits et
`CORS_ORIGIN`.

### Santé

```bash
curl http://localhost:5000/api/v1/health   # ok | degraded (1 service down) | down (2+), 503 si non-ok, latence par service
                                            # (/api/v1/health/services en est un alias)
```

### Diagnostic rapide

| Symptôme | Piste |
|---|---|
| Refus de démarrer : « The OpenSearch index "…" (OPENSEARCH_INDEX) does not exist » | `OPENSEARCH_INDEX` est absente ou ne désigne aucun index. Vérifier `.env.dev`, puis lancer l'ingestion : `kedro run` dans `data/`. |
| Part `error` « Serving contract violated » | Un document OpenSearch, son document Mongo ou ses offsets ne respectent pas le contrat ; le message cite l'`identifier` ou le `chunk_id`. Réingérer le corpus. |
| 0 source sur toutes les questions | Index vide : lancer l'ingestion. |
| Log `LLM context capped` | Les passages dépassaient 200 000 caractères : les derniers du classement n'ont pas été lus par le LLM. Les sources sont toutes affichées. |
| Embedding indisponible | Conteneur TEI (GPU requis) — `npm run logs` depuis la racine. |
| LLM timeout / 4xx | `LLM_API_ENDPOINT` / `LLM_API_KEY` / `LLM_MODEL` ; augmenter `LLM_TIMEOUT` si réseau lent. |
