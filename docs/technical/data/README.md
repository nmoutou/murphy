# Documentation — data

Documentation technique du pipeline d'**ingestion** de Murphy : LEGIFRANCE XML → parse →
chunk → embed → MongoDB / Qdrant / Neo4j. Le pipeline tourne hors-ligne, hors de la stack
Docker de serving ; il ne partage avec le backend que les bases de données.

## Quoi lire, dans quel ordre

| Document | Contenu |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Vue d'ensemble : le shell Kedro, le cœur `ragcore` (hexagonal), le DAG, les principes de conception. **Commencer ici.** |
| [reference/pipeline.md](reference/pipeline.md) | Le déroulé exhaustif d'un run, nœud par nœud, avec le pool de workers et les barrières du DAG. |
| [reference/sources.md](reference/sources.md) | Les sources DILA, les connecteurs, le parser générique (table de rôles), le chunking, l'extraction de relations et de citations. |
| [reference/modele-de-donnees.md](reference/modele-de-donnees.md) | Les modèles Pydantic et ce qui est réellement écrit dans Mongo (les deux bases), Qdrant et Neo4j — collections, index, schémas. |
| [reference/configuration.md](reference/configuration.md) | `parameters.yml` champ par champ, le `.env.dev` racine, la scission workflow/infra et le fingerprint qui nomme les collections Qdrant. |
| [reference/idempotence-et-publication.md](reference/idempotence-et-publication.md) | Le manifest, INSERT/UPDATE/EXCLUDED, la saga et ses compensations, `nuke_all`, et la publication du pointeur de collection. |
| [reference/telemetrie.md](reference/telemetrie.md) | Le catalogue d'événements, les backends (console/JSONL/Mongo/agrégat), l'équation de complétude et le statut `ok`/`degraded`/`failed`, MLflow. |

---

## Opérations

### Prérequis

- Python ≥ 3.11 (venv dans `data/.venv`), installé par `uv sync --extra dev`, comme en CI.
- Les bases (Mongo, Qdrant, Neo4j) et le service d'embedding TEI, déclarés à la **racine du
  dépôt** : `npm run ingest:up` depuis la racine (ou `npm run up` depuis `data/`) les démarre (TEI exige un GPU NVIDIA ; le
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

- `ENVIRONMENT=dev` est requis pour `nuke_all`, l'interrupteur d'embedding et
  l'hydratation Neo4j — l'absence de la variable vaut `prod`, donc tout est verrouillé.
- `EMBEDDING_PROVIDER` : `openai` (TEI) pour un vrai run ; le défaut est `noop`
  (vecteurs **nuls**, hygiène de test uniquement).

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

- les corpus dans Mongo `LEGIFRANCE`, Qdrant (collection nommée par empreinte) et Neo4j ;
- le bilan (`RunSummary`) dans `data/08_reporting/stats/*.json` et Mongo
  `MURPHY_META.meta_run_summaries` ;
- la trace événementielle dans `data/08_reporting/events/*.jsonl` et
  `MURPHY_META.meta_audit_events` ;
- si et seulement si le run est `ok` : le **pointeur de collection publiée**
  (`MURPHY_META.meta_published_collection`) que le backend lit au boot.

### Développer

```bash
ruff check .        # lint (+ format : ruff format)
pytest              # tests unitaires + golden — AUCUNE base ni .env.dev requis
pytest -m integration   # tests d'intégration (testcontainers), exclus par défaut
mypy                # typage strict sur src/ragcore (config dans pyproject.toml)
```

Extras optionnels (`pyproject.toml`) : `embedding-local` (sentence-transformers/torch,
uniquement pour `EMBEDDING_PROVIDER=local`), `tracking` (MLflow, pour lire l'A/B),
`notebooks`, `docs`, `dev`.

### Diagnostic rapide

| Symptôme | Piste |
|---|---|
| `FileNotFoundError` au démarrage sur `.env.dev` | Le fichier vit à la **racine du dépôt**, pas dans `data/`. |
| Run « ok » mais 0 document | `XML_SOURCE_PATH` ne pointe sur rien (un répertoire absent ne lève pas — il donne zéro document) ; vérifier le chemin et les sous-répertoires par source. |
| `nuke_all refusé` | `ENVIRONMENT` ≠ `dev` dans le `.env.dev` racine — c'est le garde-fou voulu. |
| Avertissement « vecteurs NULS » | `EMBEDDING_PROVIDER=noop` (le défaut). Passer à `openai` + `EMBEDDING_SERVICE_URL` pour un vrai run. |
| Le run échoue avant d'ingérer, en nommant un modèle | La précondition TEI : le modèle servi par le conteneur (`GET /info`) diverge de `parameters.yml`. Aligner les deux. |
| `chunk.truncated` non nul au bilan | Le `chunk_size` configuré dépasse la fenêtre du modèle d'embedding : le corpus est complet mais des fins de chunks ne sont pas indexées — baisser `chunk_size`. |
| Le backend ne trouve rien après un run | Le run était-il `ok` ? Un run `degraded` **ne publie pas** le pointeur ; le serving reste sur le dernier corpus complet. Lire le bilan dans `meta_run_summaries`. |
