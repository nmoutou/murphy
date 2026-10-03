# Documentation — data

Documentation technique du pipeline d'**ingestion** de Murphy : LEGIFRANCE XML → parse →
chunk → embed → MongoDB / Qdrant / Neo4j. Le pipeline tourne hors-ligne, hors de la stack
Docker de serving ; il ne partage avec le backend que les bases de données.

## Quoi lire, dans quel ordre

| Document | Contenu |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Vue d'ensemble : le shell Kedro, le cœur `ragcore` (hexagonal), le DAG, les principes de conception. **Commencer ici.** |
| [reference/pipeline.md](reference/pipeline.md) | Le déroulé exhaustif d'un run, nœud par nœud, avec le pool de workers et les barrières du DAG. |
| [reference/sources.md](reference/sources.md) | Les sources DILA, les connecteurs, le parser générique (table de rôles), le chunking, l'extraction des relations et des relations non formatées. |
| [reference/modele-de-donnees.md](reference/modele-de-donnees.md) | Les modèles Pydantic et ce qui est réellement écrit dans Mongo (les deux bases), Qdrant et Neo4j — collections, index, schémas. |
| [reference/analyseurs.md](reference/analyseurs.md) | Les analyseurs OpenSearch `fr_juridique` et `references` (ADR-028) : l'inventaire des références du corpus, leurs définitions, les cas vérifiés par `_analyze`. |
| [reference/configuration.md](reference/configuration.md) | `parameters.yml` champ par champ et le `.env.dev` racine. |
| [reference/idempotence.md](reference/idempotence.md) | La réécriture en place, la saga et ses compensations, `nuke_all`. |
| [reference/telemetrie.md](reference/telemetrie.md) | Le vocabulaire des événements, les backends (console/agrégat), l'équation de complétude et le statut `ok`/`degraded`/`failed`. |

---

## Opérations

### Prérequis

- Python ≥ 3.11 (venv dans `data/.venv`), installé par `uv sync --extra dev`, comme en CI.
- Les bases (Mongo, Qdrant, Neo4j) et le service d'embedding TEI, déclarés à la **racine du
  dépôt** : `npm run up`, depuis la racine ou depuis `data/`, les démarre avec le reste de la stack (TEI exige un GPU NVIDIA ; le
  premier boot télécharge le modèle — patience, ce n'est pas un blocage).
- Le corpus XML DILA sous `XML_SOURCE_PATH` (chemin **absolu**, hors dépôt — défaut
  `/mnt/data/Murphy/src`), avec un sous-répertoire par source : `LEGI/`, `CAPP/`, `CASS/`,
  `INCA/`, `JADE/`, `CONSTIT/`.

### Configuration

Il y a **un seul** fichier d'environnement, et il vit à la **racine du dépôt** :
`../.env.dev` (copié depuis `../.env.example`). Il n'y a pas de `.env` dans `data/` — en
créer un n'a aucun effet : `ragcore/adapters/config/settings.py` lit le fichier racine par
chemin absolu, et **lève** s'il est absent (fail-fast, pas de défauts silencieux).

Les variables et leur sémantique : voir [reference/configuration.md](reference/configuration.md).
Points critiques :

- `ENVIRONMENT=dev` applique `parameters.yml` : `nuke_all`, l'interrupteur
  d'embedding, l'ingestion des balises non configurées, les chemins des fichiers source
  (Mongo et Neo4j) et l'hydratation Neo4j. Ailleurs,
  le fichier est ignoré (avertissement au log) ; l'absence de la variable vaut `prod`, et
  toute valeur autre que `dev` ou `prod` arrête le run.
- `EMBEDDING_MODEL` et `EMBEDDING_SERVICE_URL` sont obligatoires : TEI est le seul
  embedder, et il doit être démarré (`npm run up`) avant un run.

### Lancer un run

```bash
kedro run                            # toutes les sources ingérables (les six)
kedro run --params source=cass       # une seule source
kedro run --params source=cass,jade  # un sous-ensemble
kedro viz                            # visualiser le DAG
```

Une faute de frappe dans `source=` échoue **au démarrage** en nommant les sources valides —
jamais de run silencieusement vide.

Ce qu'un run laisse derrière lui :

- les corpus dans Mongo `MURPHY_DATA`, Qdrant (collection `QDRANT_COLLECTION`) et Neo4j ;
- le bilan (`RunSummary`) dans `MURPHY_META.run_summaries`.

### Développer

```bash
ruff check .        # lint (+ format : ruff format)
pytest              # tests unitaires + golden — AUCUNE base ni .env.dev requis
pytest -m integration   # tests d'intégration (testcontainers), exclus par défaut
mypy                # typage strict sur src/ragcore (config dans pyproject.toml)
```

Extras optionnels (`pyproject.toml`) : `notebooks`, `docs`, `dev`.

### Diagnostic rapide

| Symptôme | Piste |
|---|---|
| `FileNotFoundError` au démarrage sur `.env.dev` | Le fichier vit à la **racine du dépôt**, pas dans `data/`. |
| Run « ok » mais 0 document | `XML_SOURCE_PATH` ne pointe sur rien (un répertoire absent ne lève pas — il donne zéro document) ; vérifier le chemin et les sous-répertoires par source. |
| Avertissement « parameters.yml est ignoré » | `ENVIRONMENT=prod`, ou absente, dans le `.env.dev` racine : `nuke_all` n'efface rien, l'embedding est calculé — c'est le garde-fou voulu. |
| `ValidationError` sur `environment` au démarrage | `ENVIRONMENT` ne vaut ni `dev` ni `prod` (casse comprise) : corriger la valeur. |
| Le run échoue avant d'ingérer, en nommant un modèle | La précondition TEI : le modèle servi par le conteneur (`GET /info`) n'est pas `EMBEDDING_MODEL`. Redémarrer TEI après avoir changé la variable (`npm run up`). |
| Le run échoue avant d'ingérer sur « sonde de dimension » ou « Impossible d'interroger » | TEI n'est pas joignable à `EMBEDDING_SERVICE_URL` : le démarrer (`npm run up`, ~4 min) ou corriger l'URL. |
| `chunk.truncated` non nul au bilan | Le `CHUNKING_MAX_CHARS` configuré dépasse la fenêtre du modèle d'embedding : le corpus est complet mais des fins de chunks ne sont pas indexées — baisser `CHUNKING_MAX_CHARS`. |
| Le backend ne trouve rien après un run | Le run était-il `ok` ? Un run `degraded` a laissé un corpus incomplet dans la collection servie. Lire le bilan dans `run_summaries`, puis relancer. |
