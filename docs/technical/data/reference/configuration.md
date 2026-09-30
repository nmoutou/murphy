# Configuration

Deux surfaces :

| Surface | Fichier | Contenu |
|---|---|---|
| **Réglages du pipeline** | `conf/base/parameters.yml` | Découpe, modèle d'embedding, exportation, maintenance |
| **Infra** (`InfraSettings`, `EmbeddingRuntimeSettings`) | `.env.dev` à la **racine du dépôt** | Le *où* et le *comment* : bases, secrets, chemins, nom de la collection Qdrant |

`parameters.yml` illisible = run arrêté, jamais de défauts silencieux. Le fichier est
validé **en entier** par un modèle strict (`orchestration/kedro/parameters_model.py`),
avant tout nœud : une clé inconnue, absente ou mal typée arrête le run, et toutes les
erreurs sont listées ensemble, chacune par son chemin (`` `maintenance.nuke_all` ``).
Strict veut dire sans conversion : `"false"` n'est pas un booléen, `"384"` n'est pas un
entier. Kedro fusionne les `--params` dans les paramètres : le modèle les voit aussi, et
seul `source` y est accepté (`--params sorce=cass` est refusé).

## La collection Qdrant : un nom fixe

La collection s'appelle `QDRANT_COLLECTION` (`.env.dev`), et le backend lit la même
variable (ADR-042). Il n'y a **qu'une** collection, réécrite en place à chaque run.
Conséquence : changer `chunking` ou `embedding` invalide les vecteurs déjà écrits, sans
que rien ne les sépare des nouveaux — après un tel changement, **réingérer tout le
corpus** (`nuke_all` en dev).

## `parameters.yml`, champ par champ

### `chunking` et `embedding` — ce qui décide des vecteurs

Obligatoires, sans défaut dans le code (`core/models/processing.py`) : un bloc absent, un
champ manquant, mal typé ou inconnu arrête le run au démarrage.

| Clé | Valeur | Effet |
|---|---|---|
| `chunking.size` | `384` | En **caractères** (la fenêtre du modèle est en tokens ; ratio mesuré : 3,08 car/token en moyenne, 0,33 au pire). 384 est le plus grand qui tienne : ≤ 300 tokens mesurés au tokenizer du modèle sur les six sources, **zéro document perdu** (512 en perdait 1, 1024 en perdait 98). C'est aussi le levier de coût : l'embedding est ~99,9 % du temps d'un run, et 128 → 384 l'a divisé par ~5 (838 s → 173 s). |
| `chunking.overlap` | `25` | Recouvrement de la fenêtre glissante (doit rester < `size`). |
| `embedding.model_name` | `sentence-transformers/all-mpnet-base-v2` | Doit être le modèle que sert le conteneur TEI — vérifié au démarrage (`GET /info`). |
| `embedding.dimension` | `768` | Taille des vecteurs (et de la collection Qdrant). |

### `embedding_runtime` — l'interrupteur

| Clé | Valeur | Effet |
|---|---|---|
| `enabled` | `true` | **L'interrupteur d'embedding (ADR-023).** `false` = aucun vecteur calculé ni écrit (Qdrant vide, Mongo/Neo4j normaux) — le régime d'itération dev sur le modèle de données. **Sans effet hors `ENVIRONMENT=dev`** (arbitré par le plan du run). Distinct de `EMBEDDING_PROVIDER=noop`, qui calcule et ÉCRIT des vecteurs nuls. Le transport n'est pas ici : taille de lot dans `EMBEDDING_BATCH_SIZE`, timeout codé en dur (120 s). |

### `exportation`

| Clé | Valeur | Effet |
|---|---|---|
| `skip_unconfigured` | `false` | Le sort des balises non-configurées (cadrage « trois portes ») : `false` = la balise entre en metadata sous sa clé chemin-complet ; `true` = retirée du document. **Sans effet hors `ENVIRONMENT=dev`** : la balise est toujours retirée (ADR-022 §1, arbitré par le plan du run). Le signal `tag.unconfigured`, lui, est TOUJOURS émis — on compte d'abord, on filtre ensuite. |
| `neo4j.include_path` / `include_content` | `true` / `true` | Hydratation des nœuds Neo4j **en dev seulement** (forcés à `false` ailleurs — ADR-022 §2) : chemins des fichiers XML source, texte du document (`_text_content`). |
| `neo4j.labels.default` / `labels.by_prefix` | `Document` / `LEGIARTI: Article`, `LEGITEXT: Texte`, `LEGISCTA: Section` | Le label d'un nœud Neo4j d'après les 8 lettres de son identifiant ; un préfixe absent de la table reçoit `default`. `by_prefix` est obligatoire (`{}` accepté). Préfixe qui n'est pas 8 majuscules ou label mal formé = échec au démarrage. S'applique en dev comme en prod. Changer la table sans `nuke_all` laisse l'ancien label sur les nœuds déjà écrits. |

### `maintenance`

| Clé | Valeur | Effet |
|---|---|---|
| `nuke_all` | `true` | Efface TOUTES les données de TOUTES les bases en tête de run (Mongo documents+manifest, graphe Neo4j, **toutes** les collections Qdrant), en **préservant `MURPHY_META`**. Le levier disque du développement. Hors `ENVIRONMENT=dev` (l'absence de la variable vaut `prod`), `true` arrête le run dans le plan du run, avant tout nœud (`NukeAllOutsideDevError`). |

## `.env.dev` (racine du dépôt)

**Un seul fichier, par chemin absolu** (`settings.py:ROOT_ENV_FILE`) — jamais résolu
depuis le CWD (un `kedro run` lancé d'ailleurs prendrait silencieusement tous les
défauts, dont `provider=noop`). Absent = levée à l'instanciation des settings (pas à
l'import : les tests unitaires n'en ont pas besoin). Un seul fichier parce que le
conteneur TEI et le pipeline doivent lire **la même** variable de modèle : deux fichiers
pourraient diverger, et une divergence écrit les vecteurs d'un autre modèle que celui que
le backend interroge.

Le fichier porte les URLs **côté hôte** (`localhost`) : le pipeline tourne sur l'hôte,
et c'est docker-compose qui surcharge les services conteneurisés avec leurs noms de
service.

### `InfraSettings`

| Variable | Défaut | Rôle |
|---|---|---|
| `ENVIRONMENT` | `prod` | **Le défaut penche vers le refus** : il garde `nuke_all`, l'interrupteur d'embedding, l'hydratation Neo4j et l'ingestion des balises non configurées. Un `.env` incomplet est traité comme protégé. |
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

Comment on **atteint** le modèle — jamais quel modèle (lui est dans `parameters.yml`).

| Variable | Défaut | Rôle |
|---|---|---|
| `EMBEDDING_PROVIDER` | `noop` | `openai` (TEI/compatible — le vrai run), `local` (sentence-transformers, extra `embedding-local`), `noop` (vecteurs **nuls**, écrits dans la collection du vrai modèle — hygiène de test, bruyamment signalée). |
| `EMBEDDING_SERVICE_URL` | — | L'URL du service (vide = absente). |
| `EMBEDDING_API_KEY` | — | Clé éventuelle (vide = absente — sinon `Bearer` vide et 401 inexpliqué). |
| `EMBEDDING_BATCH_SIZE` | `32` | Taille de lot du provider. |

## Les quatre garde-fous dev/prod

Même asymétrie pour les quatre : le YAML propose, l'environnement **arbitre**, et hors
`dev` le comportement sûr gagne quoi que dise le fichier. Les clés sont validées partout,
avant l'arbitrage : une coquille arrête le run même en prod.

| Levier | En `dev` | Hors `dev` |
|---|---|---|
| `maintenance.nuke_all` | Efface tout (sauf MURPHY_META) | **Lève** `NukeAllOutsideDevError` dans le plan du run, avant tout nœud |
| `embedding_runtime.enabled` | Peut couper l'embedding | Ignoré : on embarque toujours |
| `exportation.neo4j.*` | Hydratation ouverte par défaut | Ignorés : nœud maigre |
| `exportation.skip_unconfigured` | Peut ingérer les balises non configurées | Ignoré : toujours retirées |
