# Configuration

Deux surfaces :

| Surface | Fichier | Contenu |
|---|---|---|
| **Réglages de dev** | `conf/base/parameters.yml` | Les commodités de développement, ignorées hors `dev` |
| **Environnement** (`InfraSettings`, `EmbeddingRuntimeSettings`, `ChunkingSettings`) | `.env.dev` à la **racine du dépôt** | Le *où* et le *comment* : bases, secrets, chemins, nom de la collection Qdrant, modèle d'embedding servi par TEI, et la découpe, qui en dépend |

`parameters.yml` illisible = run arrêté, jamais de défauts silencieux. Le fichier est
validé **en entier** par un modèle strict (`orchestration/kedro/parameters_model.py`),
avant tout nœud : une clé inconnue, absente ou mal typée arrête le run, et toutes les
erreurs sont listées ensemble, chacune par son chemin (`` `include_path` ``).
Strict veut dire sans conversion : `"false"` n'est pas un booléen. Kedro fusionne les
`--params` à la racine des paramètres : le modèle les voit aussi. Seul `source` y est
accepté, et il est rangé à part avant la validation, parce qu'il vaut aussi en prod
(`--params sorce=cass` est une clé inconnue).

## La collection Qdrant : un nom fixe

La collection s'appelle `QDRANT_COLLECTION` (`.env.dev`), et le backend lit la même
variable (ADR-042). Il n'y a **qu'une** collection, réécrite en place à chaque run.
Conséquence : changer `CHUNKING_*` ou `EMBEDDING_MODEL` invalide les vecteurs déjà écrits, sans
que rien ne les sépare des nouveaux — après un tel changement, **réingérer tout le
corpus** (`nuke_all` en dev).

## `parameters.yml`, champ par champ

Il ne porte que des commodités de développement, à la racine du fichier. Un bloc
`chunking` ou `dev` resté d'une ancienne forme est une clé inconnue : le run s'arrête (la
découpe vit dans l'environnement, voir `ChunkingSettings`).

Le YAML propose, l'environnement **arbitre** (`run_parameters.resolve_dev_settings`) :
en `ENVIRONMENT=dev`, le fichier s'applique tel quel ; ailleurs (l'absence de la variable
vaut `prod`), il est **remplacé en entier** par les valeurs sûres, et le plan du run
journalise un avertissement. Les clés restent obligatoires et validées partout : une
coquille arrête le run même en prod.

| Clé | Valeur | En `dev` | Hors `dev` |
|---|---|---|---|
| `nuke_all` | `true` | Efface TOUTES les données de TOUTES les bases en tête de run (Mongo `documents`, graphe Neo4j, **toutes** les collections Qdrant), en **préservant `MURPHY_META`**. Le levier disque du développement. | Rien n'est effacé. |
| `embedding_enabled` | `true` | **L'interrupteur d'embedding (ADR-023).** `false` = aucun vecteur calculé ni écrit (Qdrant vide, Mongo/Neo4j normaux) — le régime d'itération sur le modèle de données. TEI doit quand même tourner : le modèle servi est vérifié et la dimension mesurée au démarrage. | On embarque toujours. |
| `skip_unconfigured` | `false` | Le sort des balises non configurées (cadrage « trois portes ») : `false` = la balise entre en metadata sous sa clé chemin-complet ; `true` = retirée du document. Le signal `tag.unconfigured`, lui, est TOUJOURS émis — on compte d'abord, on filtre ensuite. | Toujours retirées (ADR-022 §1). |
| `include_path` | `true` | Les chemins des fichiers XML source (`source_files`), dans le document Mongo **et** sur le nœud Neo4j. Repasser à `false` sans `nuke_all` : Mongo les perd au run suivant (`replace_one` remplace le document entier), mais Neo4j les garde (`SET +=` n'efface aucune propriété). | Aucun chemin écrit (ADR-022 §4). |
| `include_content_neo4j` | `true` | Le texte du document sur son nœud Neo4j (`_text_content`), en plus de ses métadonnées, toujours là en dev. Repasser à `false` sans `nuke_all` laisse le texte déjà écrit (`SET +=`). | Nœud maigre (ADR-022 §2). |

Rien de l'embedding n'est dans `parameters.yml` : le modèle, l'URL de TEI, la taille de
lot et le timeout sont dans l'environnement (voir `EmbeddingRuntimeSettings`).

## `.env.dev` (racine du dépôt)

**Un seul fichier, par chemin absolu** (`settings.py:ROOT_ENV_FILE`) — jamais résolu
depuis le CWD (un `kedro run` lancé d'ailleurs prendrait silencieusement tous les
défauts). Absent = levée à l'instanciation des settings (pas à
l'import : les tests unitaires n'en ont pas besoin). Un seul fichier parce que TEI, le
backend et le pipeline doivent lire **la même** variable de modèle, `EMBEDDING_MODEL` :
deux sources pourraient diverger, et une divergence écrit les vecteurs d'un autre modèle
que celui que le backend interroge.

Le fichier porte les URLs **côté hôte** (`localhost`) : le pipeline tourne sur l'hôte,
et c'est docker-compose qui surcharge les services conteneurisés avec leurs noms de
service.

### `InfraSettings`

| Variable | Défaut | Rôle |
|---|---|---|
| `ENVIRONMENT` | `prod` | `dev` ou `prod` (ADR-043). **Le défaut penche vers le refus** : seul `dev` applique `parameters.yml` (`nuke_all`, interrupteur d'embedding, balises non configurées, chemins des fichiers source, hydratation Neo4j). Absente ou vide, la variable vaut `prod` : un `.env` incomplet est traité comme protégé. Toute autre valeur (`Dev`, `development`…) arrête le run au chargement de la configuration, avant tout nœud. |
| `MONGODB_URI` | `mongodb://localhost:27017` | |
| `MONGODB_DATA_DB_NAME` | `LEGIFRANCE` | Données : `documents`. |
| `MONGODB_META_DB_NAME` | `MURPHY_META` | Méta : audit, bilans, pendantes. |
| `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` | `bolt://localhost:7687` / `neo4j` / `neo4j` | Mot de passe en `SecretStr`. |
| `QDRANT_URL` / `QDRANT_API_KEY` | `http://localhost:6333` / — | Clé vide = absente (validator). |
| `QDRANT_COLLECTION` | — (**obligatoire**) | Le nom fixe de la collection Qdrant, lu aussi par le backend. Absente = levée au chargement des settings. |
| `XML_SOURCE_PATH` | `/mnt/data/Murphy/src` | La racine du corpus, **absolue** (un chemin relatif absent ne lève pas — il donne zéro document, indiscernable d'un run réussi). |
| `SOURCE` | `all` | Les sources d'un run nu. `all` = les six ingérables (un défaut `legi` laissait cinq bases sur six intactes, en silence). Surchargeable par `--params source=…`. |

### `EmbeddingRuntimeSettings` (préfixe `EMBEDDING_`)

Le service TEI, seul embedder de l'ingestion : pas de fournisseur à choisir. Au
démarrage, le hook vérifie que TEI sert `EMBEDDING_MODEL` (`GET /info`) et mesure la
dimension des vecteurs par une requête de sonde (`served_model.inspect_served_model`) ;
la collection Qdrant est créée à cette dimension. Service injoignable, autre modèle ou
sonde en échec = run arrêté avant tout nœud.

| Variable | Défaut | Rôle |
|---|---|---|
| `EMBEDDING_MODEL` | — (**obligatoire**) | Le modèle attendu. Lu aussi par TEI (`--model-id`) et par le backend (`EMBEDDING_MODEL_NAME` via Compose). En changer invalide les vecteurs écrits : redémarrer TEI, puis réingérer tout le corpus. |
| `EMBEDDING_SERVICE_URL` | — (**obligatoire**) | L'API compatible OpenAI de TEI, p. ex. `http://localhost:5001/v1`. Vide = absente. |
| `EMBEDDING_BATCH_SIZE` | `32` | Taille de lot des requêtes à TEI. |
| `EMBEDDING_INGESTION_TIMEOUT` | `120000` | Timeout d'une requête au service, en **ms** (> 0). Distinct d'`EMBEDDING_SERVICE_TIMEOUT` (10 s), celui du backend : le backend embarque une question, l'ingestion envoie en parallèle tous les lots d'un document, qui font la queue côté GPU. |

### `ChunkingSettings` (préfixe `CHUNKING_`)

La découpe, à côté d'`EMBEDDING_MODEL` parce qu'elle en dépend : `CHUNKING_MAX_CHARS` est
le plus grand qui tienne dans la fenêtre du modèle, et se remesure quand il change. Les
deux variables sont obligatoires, sans défaut dans le code : une variable absente, vide ou
qui n'est pas un entier arrête le run au démarrage, comme une valeur hors bornes
(`ChunkingConfig`, `core/models/processing.py`). Pour essayer une valeur sans toucher au
fichier : `CHUNKING_MAX_CHARS=512 kedro run` (l'environnement du shell prime sur
`.env.dev`).

| Variable | Valeur | Effet |
|---|---|---|
| `CHUNKING_MAX_CHARS` | `384` | Taille maximale d'un chunk, en **caractères** (la fenêtre du modèle est en tokens ; ratio mesuré : 3,08 car/token en moyenne, 0,33 au pire). 384 est le plus grand qui tienne pour `all-mpnet-base-v2` : ≤ 300 tokens mesurés au tokenizer du modèle sur les six sources, **zéro document perdu** (512 en perdait 1, 1024 en perdait 98). C'est aussi le levier de coût : l'embedding est ~99,9 % du temps d'un run, et 128 → 384 l'a divisé par ~5 (838 s → 173 s). |
| `CHUNKING_OVERLAP_CHARS` | `25` | Recouvrement de la fenêtre glissante, en caractères. Doit rester < `CHUNKING_MAX_CHARS` : sinon le curseur n'avance pas, et le run s'arrête au démarrage. Ne joue que dans un bloc plus long que `CHUNKING_MAX_CHARS`, que la fenêtre coupe en plein mot : 25 caractères (3 ou 4 mots) gardent entier un mot coupé à la frontière, pas une phrase. **Non mesuré** : aucun jeu d'évaluation du retrieval n'existe pour le régler. |
