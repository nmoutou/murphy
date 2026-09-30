# Configuration

Deux surfaces :

| Surface | Fichier | Contenu |
|---|---|---|
| **Réglages du pipeline** | `conf/base/parameters.yml` | Découpe, labels du graphe, réglages de dev |
| **Infra** (`InfraSettings`, `EmbeddingRuntimeSettings`) | `.env.dev` à la **racine du dépôt** | Le *où* et le *comment* : bases, secrets, chemins, nom de la collection Qdrant, modèle d'embedding servi par TEI |

`parameters.yml` illisible = run arrêté, jamais de défauts silencieux. Le fichier est
validé **en entier** par un modèle strict (`orchestration/kedro/parameters_model.py`),
avant tout nœud : une clé inconnue, absente ou mal typée arrête le run, et toutes les
erreurs sont listées ensemble, chacune par son chemin (`` `dev.nuke_all` ``).
Strict veut dire sans conversion : `"false"` n'est pas un booléen, `"384"` n'est pas un
entier. Kedro fusionne les `--params` dans les paramètres : le modèle les voit aussi, et
seul `source` y est accepté (`--params sorce=cass` est refusé).

## La collection Qdrant : un nom fixe

La collection s'appelle `QDRANT_COLLECTION` (`.env.dev`), et le backend lit la même
variable (ADR-042). Il n'y a **qu'une** collection, réécrite en place à chaque run.
Conséquence : changer `chunking` ou `EMBEDDING_MODEL` invalide les vecteurs déjà écrits, sans
que rien ne les sépare des nouveaux — après un tel changement, **réingérer tout le
corpus** (`nuke_all` en dev).

## `parameters.yml`, champ par champ

### `chunking` — la découpe

Obligatoire, sans défaut dans le code (`core/models/processing.py`) : un bloc absent, un
champ manquant, mal typé ou inconnu arrête le run au démarrage. Le modèle d'embedding
n'est pas ici : il vient de `EMBEDDING_MODEL` (voir plus bas), et sa dimension est
mesurée auprès de TEI.

| Clé | Valeur | Effet |
|---|---|---|
| `chunking.max_chars` | `384` | Taille maximale d'un chunk, en **caractères** (la fenêtre du modèle est en tokens ; ratio mesuré : 3,08 car/token en moyenne, 0,33 au pire). 384 est le plus grand qui tienne : ≤ 300 tokens mesurés au tokenizer du modèle sur les six sources, **zéro document perdu** (512 en perdait 1, 1024 en perdait 98). C'est aussi le levier de coût : l'embedding est ~99,9 % du temps d'un run, et 128 → 384 l'a divisé par ~5 (838 s → 173 s). |
| `chunking.overlap_chars` | `25` | Recouvrement de la fenêtre glissante, en caractères. Doit rester < `max_chars` : sinon le curseur n'avance pas, et le run s'arrête au démarrage. Ne joue que dans un bloc plus long que `max_chars`, que la fenêtre coupe en plein mot : 25 caractères (3 ou 4 mots) gardent entier un mot coupé à la frontière, pas une phrase. **Non mesuré** : aucun jeu d'évaluation du retrieval n'existe pour le régler. |

### `node_labels` — le graphe, en dev comme en prod

| Clé | Valeur | Effet |
|---|---|---|
| `default` / `by_prefix` | `Document` / `LEGIARTI: Article`, `LEGITEXT: Texte`, `LEGISCTA: Section` | Le label d'un nœud Neo4j d'après les 8 lettres de son identifiant ; un préfixe absent de la table reçoit `default`. `by_prefix` est obligatoire (`{}` accepté). Préfixe qui n'est pas 8 majuscules ou label mal formé = échec au démarrage. L'écriture ajoute le label sans retirer l'ancien : après un changement de la table, un nœud déjà écrit garde l'ancien label, même réingéré (il porte alors les deux). Repartir de zéro demande `nuke_all`. |

### `dev` — les commodités de développement, ignorées hors `dev`

Le YAML propose, l'environnement **arbitre** (`run_parameters.resolve_dev_settings`) :
en `ENVIRONMENT=dev`, le bloc s'applique tel quel ; ailleurs (l'absence de la variable
vaut `prod`), il est **remplacé en entier** par les valeurs sûres, et le plan du run
journalise un avertissement. Les clés restent obligatoires et validées partout : une
coquille arrête le run même en prod.

| Clé | Valeur | En `dev` | Hors `dev` |
|---|---|---|---|
| `nuke_all` | `true` | Efface TOUTES les données de TOUTES les bases en tête de run (Mongo documents+manifest, graphe Neo4j, **toutes** les collections Qdrant), en **préservant `MURPHY_META`**. Le levier disque du développement. | Rien n'est effacé. |
| `embedding_enabled` | `true` | **L'interrupteur d'embedding (ADR-023).** `false` = aucun vecteur calculé ni écrit (Qdrant vide, Mongo/Neo4j normaux) — le régime d'itération sur le modèle de données. TEI doit quand même tourner : le modèle servi est vérifié et la dimension mesurée au démarrage. | On embarque toujours. |
| `skip_unconfigured` | `false` | Le sort des balises non configurées (cadrage « trois portes ») : `false` = la balise entre en metadata sous sa clé chemin-complet ; `true` = retirée du document. Le signal `tag.unconfigured`, lui, est TOUJOURS émis — on compte d'abord, on filtre ensuite. | Toujours retirées (ADR-022 §1). |
| `node_hydration.include_path` / `include_content` | `true` / `true` | Ce que portent en plus les nœuds Neo4j (leurs métadonnées, elles, sont toujours là en dev) : chemins des fichiers XML source (`source_files`), texte du document (`_text_content`). L'écriture (`SET +=`) n'efface aucune propriété : repasser à `false` sans `nuke_all` laisse celles déjà écrites. | Nœud maigre (ADR-022 §2). |

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
| `ENVIRONMENT` | `prod` | `dev` ou `prod` (ADR-043). **Le défaut penche vers le refus** : seul `dev` applique le bloc `dev` de `parameters.yml` (`nuke_all`, interrupteur d'embedding, balises non configurées, hydratation Neo4j). Absente ou vide, la variable vaut `prod` : un `.env` incomplet est traité comme protégé. Toute autre valeur (`Dev`, `development`…) arrête le run au chargement de la configuration, avant tout nœud. |
| `MONGODB_URI` | `mongodb://localhost:27017` | |
| `MONGODB_DATA_DB_NAME` | `LEGIFRANCE` | Données : `documents`, `manifest`. |
| `MONGODB_META_DB_NAME` | `MURPHY_META` | Méta : audit, bilans, pendantes. |
| `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` | `bolt://localhost:7687` / `neo4j` / `neo4j` | Mot de passe en `SecretStr`. |
| `QDRANT_URL` / `QDRANT_API_KEY` | `http://localhost:6333` / — | Clé vide = absente (validator). |
| `QDRANT_COLLECTION` | — (**obligatoire**) | Le nom fixe de la collection Qdrant, lu aussi par le backend. Absente = levée au chargement des settings. |
| `XML_SOURCE_PATH` | `/mnt/data/Murphy/src` | La racine du corpus, **absolue** (un chemin relatif absent ne lève pas — il donne zéro document, indiscernable d'un run réussi). |
| `SOURCE` | `all` | Les sources d'un run nu. `all` = les six ingérables (un défaut `legi` laissait cinq bases sur six intactes, en silence). Surchargeable par `--params source=…`. |
| `META_JSONL_DIR` | `data/08_reporting` | Où vivent `events/` et `stats/`. |

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
