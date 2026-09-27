# Configuration

Deux surfaces, et la frontière entre les deux est **la** décision d'architecture du
pipeline :

| Surface | Fichier | Question qui décide |
|---|---|---|
| **Workflow** (`WorkflowConfig`) | `conf/base/workflow/parameters.yml` | « En changer la valeur invalide-t-il les vecteurs déjà produits ? » → oui |
| **Infra d'ingestion** | `conf/base/ingestion/parameters.yml` | → non (tokenizing, relations, timeout/batch/enabled, exportation, maintenance) |
| **Runtime de récupération** (bloc R) | `conf/base/evaluation/parameters.yml` | → sans objet côté ingestion — consommé par P2 (placeholder, B-13) |
| **Infra** (`InfraSettings`, `EmbeddingRuntimeSettings`) | `.env.dev` à la **racine du dépôt** | → non (le *où* et le *comment*, jamais le *quoi*) |

Depuis **ADR-026** (B-14), cette frontière n'est plus qu'une convention de
commentaires : c'est une partition **physique**, en trois fichiers sous
`conf/base/`, fusionnés par le glob par défaut de Kedro (`parameters*`, qui
descend récursivement) en un seul dict de `parameters` — sans aucune
modification du loader (`CONFIG_LOADER_ARGS` dans `settings.py` est
inchangé). Les dossiers vivent sous `base/` plutôt qu'en frères de `base/`
(schéma initial de l'ADR) : Kedro ne charge que l'environnement `base_env`
par défaut, un dossier frère ne serait simplement jamais lu.

## Le fingerprint — pourquoi la scission est structurelle

La collection Qdrant est **nommée par le hash** de la `WorkflowConfig`
(`core/config/fingerprint.py`) : blake2b de la forme canonique JSON (clés triées, floats
normalisés, ASCII), 32 caractères hexadécimaux. Conséquences :

- changer `chunk_size`, la version de normalisation ou le modèle d'embedding **crée
  mécaniquement une collection neuve** — les vecteurs d'avant et d'après ne sont pas
  comparables et ne cohabitent jamais. Les deux collections coexistent, chacune
  rejouable : c'est ce qui rend l'A/B possible ;
- déménager Mongo, changer de provider d'embedding ou passer de 4 à 8 workers ne change
  **rien** : ces champs ne sont pas dans le type, donc `fingerprint()` n'y a
  *physiquement* pas accès. L'erreur « j'ai hashé une URI et fragmenté mes collections »
  est impossible par construction, pas déconseillée ;
- même config → même hash, **pour toujours** : le golden test
  `tests/golden/test_fingerprint.py` fige des hashs littéraux — les changer est un geste
  visible en revue ;
- l'opacité du hash est assumée : elle est levée par le tracking (le run MLflow porte la
  `WorkflowConfig` en clair, et son run-id EST le nom de collection), pas par un nom
  « parlant » qui redeviendrait fragile.

Le YAML ne fait que **peupler** la `WorkflowConfig`
(`run_parameters.py:build_workflow_config`, seule traduction du dépôt, qui lit désormais la clé
top-level `workflow:`) ; l'objet est la vérité, le YAML une façon de le remplir. Illisible
= run arrêté, jamais de défauts silencieux.

## `parameters.yml`, champ par champ

### `workflow` (`conf/base/workflow/parameters.yml`) — ce qui entre dans le hash

| Clé | Valeur | Effet |
|---|---|---|
| `normalization.version` | `v1` | **Hashée.** Doit rester synchronisée avec `NORMALIZATION_VERSION` (`sources/generic/normalize.py`) : changer le traitement sans changer la version mélangerait deux jeux de vecteurs incomparables dans la même collection. |
| `chunking.strategy` | `legi-structural-v1` | **Hashée.** Nomme la méthode de découpe. |
| `chunking.chunk_size` | `384` | **Hashée.** En **caractères** (la fenêtre du modèle est en tokens ; ratio mesuré : 3,08 car/token en moyenne, 0,33 au pire). 384 est le plus grand qui tienne : ≤ 300 tokens mesurés au tokenizer du modèle sur les six sources, **zéro document perdu** (512 en perdait 1, 1024 en perdait 98). C'est aussi le levier de coût : l'embedding est ~99,9 % du temps d'un run, et 128 → 384 l'a divisé par ~5 (838 s → 173 s). |
| `chunking.chunk_overlap` | `25` | **Hashée.** Recouvrement de la fenêtre glissante (doit rester < chunk_size). |
| `embedding.embedding_model` | `sentence-transformers/all-mpnet-base-v2` | **Hashée.** Doit être le modèle que sert le conteneur TEI — vérifié au démarrage (`GET /info`). |
| `embedding.dimension` | `768` | **Hashée.** Taille des vecteurs (et de la collection Qdrant). |

Ce fichier ne contient **que** du hashé (règle invariante ADR-026) : aucune
URI, secret, chemin ou paramètre d'infra n'y a sa place.

### `importation` (`conf/base/ingestion/parameters.yml`)

| Clé | Valeur | Effet |
|---|---|---|
| `extraction.content_tag` | `CONTENU` | Balise de contenu à l'extraction. |
| `validation.validation_rules.require_eli` | `true` | Un document LEGI sans ELI est rejeté (EXCLUDED). |
| `validation.validation_rules.format_regex` | `^[A-Z]{8}[0-9]{12}$` | Le motif d'un identifiant DILA — le même que `ELI_PATTERN` dans le code et que le déclencheur lien de la cascade. |
| `normalization.title_mapping` | mappings par racine | D'où vient le `title` de chaque type de document. |

### `formatting` — infra uniquement (le hashé a migré vers `workflow`)

| Clé | Valeur | Effet |
|---|---|---|
| `tokenizing.*` | spaCy `fr_core_news_sm` | Vestige : spaCy a quitté le chemin critique (plus de lemmatisation). |
| `relations.filtering` / `invert` / `mappings` / `reduction` | — | La table de traitement des liens : types inversés (`txt_source`, `lien_art`, `lien_section_ta`), mapping des `typelien` vers les verbes (`titre`, `source`…), réduction transitive activée sur `titre` (la contenance). |

### `embedding_runtime` — l'infra extraite du bloc embedding

| Clé | Valeur | Effet |
|---|---|---|
| `embedding_service_timeout` / `batch_size` | `30` / `32` | Transport — non hashés (le batch effectif du provider `openai` vient de `EMBEDDING_BATCH_SIZE` côté env). |
| `enabled` | `true` | **L'interrupteur d'embedding (ADR-023).** `false` = aucun vecteur calculé ni écrit (Qdrant vide, Mongo/Neo4j normaux) — le régime d'itération dev sur le modèle de données. **Sans effet hors `ENVIRONMENT=dev`** (garde dans le hook). Pas hashé : ne pas produire de vecteurs n'invalide aucun vecteur. Distinct de `EMBEDDING_PROVIDER=noop`, qui calcule et ÉCRIT des vecteurs nuls. |

### `exportation`

| Clé | Valeur | Effet |
|---|---|---|
| `unconfigured` | `ingest` | Le sort des balises non-configurées (cadrage « trois portes ») : `ingest` = la balise entre en metadata sous sa clé chemin-complet ; `skip` = retirée du document (prod). Le signal `tag.unconfigured`, lui, est TOUJOURS émis — on compte d'abord, on filtre ensuite. Valeur invalide = échec au démarrage. |
| `neo4j.include_path` / `include_content` | `true` / `true` | Hydratation des nœuds Neo4j **en dev seulement** (forcés à `false` ailleurs — ADR-022 §2) : chemins des fichiers XML source, texte du document (`_text_content`). |
| `mongodb.database` / `collection` | `LEGIFRANCE` / `chunks` | ⚠️ **Vestige non lu** : les noms réels viennent du `.env` (`MONGODB_DATA_DB_NAME`) et des dépôts (`documents`, `manifest`). |
| `qdrant.distance` / `batch_size` | `Cosine` / `100` | ⚠️ **Vestige non lu** : la distance est codée en dur (COSINE) et il n'y a pas de `collection:` — elle est **dérivée** du fingerprint, la nommer ici permettrait d'écraser les vecteurs d'une stratégie avec ceux d'une autre. |

### `maintenance`

| Clé | Valeur | Effet |
|---|---|---|
| `cleanup_enabled` / `cache_paths` | `true`, `data/cache` + `data/meta/events` | Nettoyage de fichiers en tête de run (node `cleanup`). |
| `nuke_all` | `true` | Efface TOUTES les données de TOUTES les bases en tête de run (Mongo documents+manifest, graphe Neo4j, **toutes** les collections Qdrant), en **préservant `MURPHY_META`**. Refuse de tourner si `ENVIRONMENT != dev` (l'absence de la variable vaut `prod`). Le levier disque du développement — à ne jamais activer en prod. |

## `.env.dev` (racine du dépôt)

**Un seul fichier, par chemin absolu** (`settings.py:ROOT_ENV_FILE`) — jamais résolu
depuis le CWD (un `kedro run` lancé d'ailleurs prendrait silencieusement tous les
défauts, dont `provider=noop`). Absent = levée à l'instanciation des settings (pas à
l'import : les tests unitaires n'en ont pas besoin). Un seul fichier parce que le
conteneur TEI et le pipeline doivent lire **la même** variable de modèle : deux fichiers
pourraient diverger, et une divergence écrit les vecteurs du mauvais modèle dans la
collection nommée d'après le bon.

Le fichier porte les URLs **côté hôte** (`localhost`) : le pipeline tourne sur l'hôte,
et c'est docker-compose qui surcharge les services conteneurisés avec leurs noms de
service.

### `InfraSettings`

| Variable | Défaut | Rôle |
|---|---|---|
| `ENVIRONMENT` | `prod` | **Le défaut penche vers le refus** : il garde `nuke_all`, l'interrupteur d'embedding et l'hydratation Neo4j. Un `.env` incomplet est traité comme protégé. |
| `MONGODB_URI` | `mongodb://localhost:27017` | |
| `MONGODB_DATA_DB_NAME` | `LEGIFRANCE` | Données : `documents`, `manifest`. |
| `MONGODB_META_DB_NAME` | `MURPHY_META` | Méta : audit, bilans, pendantes, pointeur. |
| `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` | `bolt://localhost:7687` / `neo4j` / `neo4j` | Mot de passe en `SecretStr`. |
| `QDRANT_URL` / `QDRANT_API_KEY` | `http://localhost:6333` / — | Clé vide = absente (validator). |
| `XML_SOURCE_PATH` | `/mnt/data/Murphy/src` | La racine du corpus, **absolue** (un chemin relatif absent ne lève pas — il donne zéro document, indiscernable d'un run réussi). |
| `SOURCE` | `all` | Les sources d'un run nu. `all` = les six ingérables (un défaut `legi` laissait cinq bases sur six intactes, en silence). Surchargeable par `--params source=…`. |
| `META_JSONL_DIR` | `data/08_reporting` | Où vivent `events/` et `stats/`. |
| `OWNER_ID` | `default` | Le propriétaire des données du run. |
| `TRACKING_PROVIDER` | `noop` | `mlflow` pour lire l'A/B (extra `tracking` requis) — le run-id MLflow est le fingerprint. |
| `MLFLOW_TRACKING_URI` | — | `None` = config MLflow ambiante (`mlruns/` local). |

### `EmbeddingRuntimeSettings` (préfixe `EMBEDDING_`)

Comment on **atteint** le modèle — jamais quel modèle (lui est hashé, dans le workflow).

| Variable | Défaut | Rôle |
|---|---|---|
| `EMBEDDING_PROVIDER` | `noop` | `openai` (TEI/compatible — le vrai run), `local` (sentence-transformers, extra `embedding-local`), `noop` (vecteurs **nuls**, écrits dans la collection du vrai modèle — hygiène de test, bruyamment signalée). Pas hashé : deux façons d'atteindre le même modèle produisent les mêmes vecteurs. |
| `EMBEDDING_SERVICE_URL` | — | L'URL du service (vide = absente). |
| `EMBEDDING_API_KEY` | — | Clé éventuelle (vide = absente — sinon `Bearer` vide et 401 inexpliqué). |
| `EMBEDDING_BATCH_SIZE` | `32` | Taille de lot du provider. |

## Les trois garde-fous dev/prod

Même asymétrie pour les trois : le YAML propose, l'environnement **arbitre**, et hors
`dev` le comportement sûr gagne quoi que dise le fichier.

| Levier | En `dev` | Hors `dev` |
|---|---|---|
| `maintenance.nuke_all` | Efface tout (sauf MURPHY_META) | **Lève** `NukeAllOutsideDevError` avant toute écriture |
| `embedding.enabled` | Peut couper l'embedding | Ignoré : on embarque toujours |
| `exportation.neo4j.*` | Hydratation ouverte par défaut | Ignorés : nœud maigre |
