# Critique de `data/conf/base/parameters.yml`

> Le fichier était `data/conf/base/ingestion/parameters.yml` jusqu'à P7.

Rédigée le 2026-09-30. Elle porte sur le fichier, sur le code qui le lit et sur les ADR 022, 023, 026 et 042.
Chemins relatifs à `data/`.

## Synthèse

| Gravité | Points |
|---|---|
| Comportement faux | P1, P2, P3, P4 |
| Paramètres morts | P5, P6 |
| Rangement | P7 à P12 |
| Valeurs et nommage | P13 à P17 |
| Validation | P18 |
| ADR | P19 à P22 |

Priorité : P1 à P4, puis P18 (qui règle P1, P2, P6 et P12).

## Clés lues et non lues

- **Lues** : `chunking`, `node_labels`, `dev.*` (depuis P11 : `nuke_all`, `embedding_enabled`, `skip_unconfigured`, `node_hydration.*`).
- **Non lues** : aucune depuis P18. Les clés mortes ont été supprimées, et le modèle strict refuse désormais toute clé inconnue.

---

## A. Comportement

### P1. Une coquille dans `unconfigured` est détectée après `nukeAll`

> **Traité** : la clé est devenue `exportation.skip_unconfigured`, un booléen strict et obligatoire, validé par `plan_run` avant tout nœud.

- **Constat** : la valeur est validée dans le nœud `computeIdempotence` (`compute_idempotence.py:42`), qui s'exécute après `cleanup` et `nukeAll`. La docstring affirme « validé au démarrage ».
- **Conséquence** : avec `unconfigured: skipp`, toutes les bases sont effacées, puis le run échoue. Une clé absente vaut `ingest` en silence.
- **Piste** : valider dans `plan_run`, avant tout nœud.

### P2. Booléens lus sans vérification de type

- **Constat** : `nuke_all` est testé tel quel (`nuke_all.py:56`) ; `enabled` et `include_*` passent par `bool(...)` (`run_parameters.py:86`, `:107-108`). Une clé absente prend un défaut silencieux.
- **Conséquence** : `nuke_all: "false"` est une chaîne non vide, donc vraie : **les bases sont effacées**.
- **Piste** : booléens stricts, clés obligatoires (voir P18).

> **Traité** : `nuke_all`, `embedding_runtime.enabled` et `neo4j.include_*` sont des booléens stricts et obligatoires, validés par `plan_run` dans tous les environnements. Le refus de `nuke_all` hors dev a lieu dans `plan_run`, avant tout nœud.
>
> Depuis P11, `nuke_all` n'arrête plus le run hors dev : il est ignoré, comme tout le bloc `dev`, et un avertissement le signale.

### P3. `cache_paths` ne vide rien, en silence

- **Constat** : les chemins sont relatifs au répertoire courant. Lancé depuis `data/`, le run vise `data/data/cache` et `data/data/meta/events`, qui n'existent pas. `_clear` renvoie 0. Les événements sont en réalité dans `data/08_reporting/events` (`META_JSONL_DIR`).
- **Contradictions** :
  - C'est le piège du chemin relatif dénoncé pour `XML_SOURCE_PATH`.
  - Corrigé, `cleanup` effacerait la télémétrie, alors que `nuke_all` s'interdit de toucher `MURPHY_META`.
  - `cleanup_enabled` n'est pas lu : impossible de désactiver le nettoyage.
- **Piste** : décider ce que « cache » désigne. Si rien : supprimer `cleanup`. Sinon : chemin absolu, et échec si le chemin est absent.

> **Traité** : « cache » ne désignait rien. Le nœud `cleanup`, `cache_paths`, `cleanup_enabled`, la sortie `cleanup_results` et l'événement `maintenance.cleanup.executed` sont supprimés. Le pipeline commence par `nukeAll`.

### P4. `unconfigured` échappe à `ENVIRONMENT`

- **Constat** : ADR-022 §1 prévoit ingestion en dev, exclusion en prod. Les trois autres réglages propres au dev sont arbitrés par l'environnement, pas celui-ci.
- **Conséquence** : un seul fichier de paramètres, sans surcouche par environnement, donc **la prod ingère les balises non configurées**.
- **Piste** : arbitrer par `ENVIRONMENT`, comme les autres (voir P11).

> **Traité** : `plan_run` arbitre `skip_unconfigured` par `ENVIRONMENT` : en dev, le YAML décide ; ailleurs, les métadonnées des balises non configurées sont toujours retirées. La clé reste validée dans tous les environnements.

---

## B. Paramètres morts

### P5. Ce que le code fait à la place

| Clé | Réalité | Faut-il la faire revivre en YAML ? |
|---|---|---|
| `nlp.spacy_model`, `formatting.tokenizing.*` | spaCy retiré, découpe en caractères. `${nlp…}` est la seule interpolation du fichier et n'alimente qu'un bloc mort. | Non |
| `importation.extraction.content_tag` | `text_holders` déclaré par source (`sources/legi/table.py:167`, `sources/juri/table.py:110`). | Non : propriété de chaque source |
| `importation.normalization.title_mapping` | `_TITLE_TAGS` (`sources/legi/table.py:45`). Les clés `Article`/`Texte`/`TexteAdmin` ne correspondent plus à rien d'actuel ; `enabled` n'a pas d'alternative. | Non |
| `formatting.relations.*` | `LinkTable` par source (`sources/legi/vocabulary.py`) et `REDUCIBLE_TYPES = {CONTAINS}` (`core/services/relation_reduction.py:42`). Verbes `titre`/`source` obsolètes ; `filtering: []` vide. | Non : table propre à LEGI, sur six sources |
| `embedding_runtime.embedding_service_timeout` | Constante `_TIMEOUT_SECONDS = 120.0` (`adapters/embedding/openai_embedder.py:21`). `.env.dev` a aussi `EMBEDDING_SERVICE_TIMEOUT=10000` (en ms, pour le backend). Trois valeurs, deux unités, une seule appliquée. | Oui, dans l'environnement, avec le reste du transport |
| `embedding_runtime.batch_size` | La valeur réelle vient de `EMBEDDING_BATCH_SIZE`. Même nom à deux endroits, un seul lu. | Supprimer du YAML |
| `exportation.mongodb.*` | La base vient de `MONGODB_DATA_DB_NAME`. La collection `chunks` n'existe pas (réelles : `documents`, `manifest`). | Non |
| `exportation.qdrant.distance` | `Distance.COSINE` en dur (`adapters/storage/qdrant/vector_repository.py:55`). Découle du modèle. | Éventuellement dans `embedding` |
| `exportation.qdrant.batch_size` | Non lu. | Selon le besoin réel |
| `maintenance.cleanup_enabled` | Non lu. | Supprimé (P3) |

**Conclusion** : les faits propres à une source (balises, titres, liens, verbes) ont été déplacés à bon escient dans les tables par source. Le YAML ne devrait contenir que ce qu'un opérateur change d'un run à l'autre.

> **Traité** : toutes les clés du tableau ont été supprimées du YAML (P18).
>
> - Le timeout d'embedding de l'ingestion est lu de `EMBEDDING_INGESTION_TIMEOUT` (ms, défaut 120000), avec le reste du transport. Il reste distinct d'`EMBEDDING_SERVICE_TIMEOUT`, celui du backend (10 s pour une question) : les deux charges n'ont pas la même durée.
> - `qdrant.distance` reste codé en dur (`Distance.COSINE`) : il découle du modèle, et un opérateur n'a pas à le changer d'un run à l'autre.

### P6. Pourquoi ces clés ont survécu

- Seuls `chunking` et `embedding` refusent les clés inconnues (`extra="forbid"`).
- Partout ailleurs, une clé inconnue ou mal orthographiée passe en silence.

> **Traité** (P18) : le modèle strict refuse les clés inconnues à tous les niveaux, `--params` compris.

---

## C. Rangement

### P7. Fichier unique dans un sous-dossier

- `ingestion/` est un vestige de la partition d'ADR-026. ADR-042 a supprimé `workflow/` sans défaire la partition.
- Tout `data/` est de l'ingestion : ce nom ne distingue rien.
- **Piste** : `conf/base/parameters.yml`.

> **Traité** : le fichier est à la racine, `conf/base/parameters.yml`, et le dossier `ingestion/` a disparu. Kedro cherche `parameters*` à la racine de `conf/base/` par défaut : aucune configuration à changer.

### P8. Des « phases » sans rapport avec le pipeline

- Numérotation 1, 3, 3 bis, 4, 5 : pas de phase 2.
- Pipeline réel : nukeAll → connect → computeIdempotence → ingest → resolveRelations → report. La maintenance, numérotée « phase 5 », s'exécute en premier.
- Le code appelle déjà « phase 1 / phase 2 » l'ingestion et la résolution des relations : deux numérotations entrent en conflit.
- Détails : « PARAMÈTRE GÉNÉRAUX » (faute d'accord), casse irrégulière des titres.

> **Traité** (P18) : avec les clés mortes, les numéros de phase ont disparu. Les titres ne nomment plus que les blocs (Découpe, Embedding, Export, Maintenance).

### P9. `exportation` est un fourre-tout

| Clé | Relève en réalité de |
|---|---|
| `unconfigured` | le parsing |
| `neo4j.labels` | le modèle de données |
| `neo4j.include_*` | le régime dev |

Depuis P18, `exportation` ne contient plus que `skip_unconfigured` et `neo4j` (`mongodb` et `qdrant`, morts, ont été supprimés).

> **Traité** (avec P11) : `exportation` a disparu. `skip_unconfigured` et `neo4j.include_*` sont dans le bloc `dev` ; les labels, qui s'appliquent en dev comme en prod, forment le bloc `node_labels`.

### P10. `embedding` / `embedding_runtime` : séparation sans objet

- La séparation « quoi / comment » servait l'empreinte d'ADR-026, qui a été supprimée.
- `embedding_runtime` n'a plus qu'une clé lue, `enabled`, qui est un choix de régime dev, pas un réglage de transport.
- Le « comment » vit en réalité dans l'environnement (`EmbeddingRuntimeSettings`) : même notion, deux emplacements.

Depuis P18, `embedding_runtime` ne contient plus que `enabled` : le timeout et la taille de lot, non lus, ont été supprimés.

> **Traité** (avec P11) : `embedding_runtime` a disparu. L'interrupteur est devenu `dev.embedding_enabled` ; `embedding` ne porte plus que le « quoi », et le « comment » reste dans l'environnement.

### P11. Réglages propres au dev éparpillés

- Quatre réglages (`nuke_all`, `embedding_runtime.enabled`, `neo4j.include_*`, `unconfigured`) dans trois blocs.
- `docs/technical/data/reference/configuration.md` regroupe déjà les trois premiers dans un tableau « garde-fous dev/prod ».
- **Piste** : un bloc `dev:` unique, ignoré hors dev. C'est l'argument d'ADR-026 : une frontière portée par la structure, pas par des commentaires.

> **Traité** : un bloc `dev` regroupe `nuke_all`, `embedding_enabled`, `skip_unconfigured` et `node_hydration.*`. Un seul arbitrage, `run_parameters.resolve_dev_settings`, l'applique en dev et le remplace ailleurs par les valeurs sûres, avec un avertissement au log. `nuke_all` suit la règle commune : hors dev, il est ignoré au lieu d'arrêter le run (`NukeAllOutsideDevError` a disparu). Les clés restent obligatoires et validées partout.

### P12. Le format du YAML est connu en plusieurs endroits

- `run_parameters.py` affirme être « le seul endroit qui connaisse la forme du YAML ». C'est faux : `pipeline.py`, `nuke_all.py` et `compute_idempotence.py` la connaissent aussi.
- Les nœuds reçoivent des blocs entiers (`params:exportation`, `params:maintenance`) pour n'en lire qu'une clé.
- `nuke_all` relit `ENVIRONMENT` lui-même au lieu de passer par le `RunPlan`.

> **Traité** (P1, P2, P3, P18) : `nukeAll` et `computeIdempotence` reçoivent un booléen du `RunPlan`, et `nuke_all` ne relit plus `ENVIRONMENT`. Depuis P3 (suppression de `cleanup`), plus aucun nœud ne reçoit de paramètre brut du YAML. Depuis P18, seul `orchestration/kedro/parameters_model.py` connaît la forme du fichier ; `run_parameters.py` n'arbitre plus que des valeurs typées.

---

## D. Valeurs et nommage

### P13. `chunking`

- L'unité n'apparaît pas dans le nom, alors que le code parle de `max_chunk_size`.
- La règle `overlap < size`, annoncée par la doc, n'est pas validée.
- `overlap: 25` n'est pas justifié (environ 8 tokens, 6,5 %), contrairement à `size`.

> **Traité** :
>
> - Les clés s'appellent `chunking.max_chars` et `chunking.overlap_chars`, partout : YAML, `ChunkingConfig`, `RunPlan`. `max_chunk_size` a disparu du chunker.
> - La règle était validée, mais tard : par le constructeur de `StructuralChunker`, dans le hook, après l'appel à TEI. `ChunkingConfig` la porte désormais, et `plan_run` l'applique avant d'ouvrir quoi que ce soit, avec les autres erreurs. Le chunker reçoit un `ChunkingConfig` et perd ses défauts `1000`/`100`.
> - `overlap_chars: 25` est documenté pour ce qu'il fait : il ne joue que dans un bloc plus long que `max_chars`, coupé en plein mot, et garde entier un mot coupé à la frontière. Il n'est pas mesuré, faute de jeu d'évaluation du retrieval : piste ouverte.

### P14. `embedding`

- `model_name` fait doublon avec `EMBEDDING_MODEL` (`.env.dev`, qui sert à TEI et au backend). La docstring de `ROOT_ENV_FILE` affirme « ils ne sont plus deux variables » : c'est faux.
- Le risque est seulement atténué par la vérification `GET /info` au démarrage.
- `dimension` est une propriété du modèle, donc redondante : elle pourrait être mesurée au démarrage plutôt que déclarée.

> **Traité** : le bloc `embedding` a quitté `parameters.yml`.
>
> - **Plus de fournisseur.** TEI est le seul embedder (`TeiEmbedder`). `EMBEDDING_PROVIDER`, `noop` (le défaut, qui écrivait des vecteurs nuls dans la collection du backend), `local` (et l'extra `embedding-local`) et `EMBEDDING_API_KEY` ont disparu. `NoopEmbedder` ne vit plus que dans les doublures de test.
> - **Le modèle** vient de `EMBEDDING_MODEL`, obligatoire, que lisent aussi TEI et le backend. La vérification `GET /info` détecte désormais un conteneur pas redémarré après un changement de la variable.
> - **La dimension** est mesurée au démarrage par une requête de sonde (`served_model.inspect_served_model`), et portée par le port `BaseEmbedder.dimension` jusqu'à la collection Qdrant.
> - La docstring de `ROOT_ENV_FILE` est vraie.
>
> Reste ouvert : une collection Qdrant qui existe déjà à une autre dimension n'est pas détectée (`ensure_collection` ne crée que si elle est absente). Après un changement de modèle sans `nuke_all`, chaque upsert échouerait. Piste : vérifier la taille de la collection existante au démarrage.

### P15. `neo4j.labels`

- `by_prefix` ne liste que trois préfixes LEGI. Les documents des cinq autres sources (`JURITEXT`, `JORFCONT`…) reçoivent tous `Document`.
- Changer un label impose un `nuke_all` : c'est un choix de schéma, pas un réglage. Il devrait être déclaré avec les sources.
- Le commentaire « 8 lettres » répète `IDENTIFIER_PREFIX_LENGTH`.

### P16. Noms ambigus

| Actuel | Problème | Proposition |
|---|---|---|
| `include_path` | Désigne les fichiers XML source, pas la hiérarchie | `include_source_files` |
| `include_content` | Stocké sous `_text_content` | aligner le nom et la propriété stockée |
| `unconfigured` | Ne dit pas de quoi il s'agit | `unconfigured_tags` |

Depuis P4 et P11, la clé est `dev.skip_unconfigured` : la proposition `unconfigured_tags` est à revoir. `include_path` et `include_content` sont désormais sous `dev.node_hydration`.

### P17. Commentaires décalés

- « À NE PAS activer en prod » : `nuke_all` est de toute façon refusé hors dev. Le commentaire devrait décrire ce refus. **Traité** (P2), puis P11 : hors dev, le bloc `dev` entier est ignoré, et son commentaire d'en-tête le dit.
- Rien n'indique l'unité de `embedding_service_timeout`. **Sans objet** (P18) : la clé, non lue, a été supprimée.

---

## E. Validation

### P18. Trois stratégies de validation coexistent

| Stratégie | Blocs |
|---|---|
| Pydantic strict | `chunking`, `embedding` |
| Validation écrite à la main | `labels`, `unconfigured` |
| `.get()` avec défaut, puis `bool()` | tout le reste |

**Piste** : un modèle pydantic unique pour tout le fichier (`extra="forbid"`, booléens stricts), validé dans `plan_run`. Les nœuds reçoivent un plan typé au lieu de dictionnaires bruts. Cela règle P1, P2, P6 et P12.

> **Traité** : `IngestionParameters` (`orchestration/kedro/parameters_model.py`) décrit tout le fichier, en `strict`, `extra="forbid"` et `frozen`. `ChunkingConfig` et `EmbeddingConfig` sont devenus stricts eux aussi. `validate_parameters` liste toutes les erreurs ensemble, chacune par son chemin pointé. Kedro fusionnant les `--params` dans les paramètres, `source` est déclaré dans le modèle : `--params sorce=cass` est refusé. Un test valide le `parameters.yml` livré.

---

## F. ADR

### P19. ADR-042 a remplacé ADR-026 à moitié

- Il a déplacé `chunking` et `embedding` dans `ingestion/` au lieu de supprimer la partition.
- Il en reste le sous-dossier et le nom `embedding_runtime`.

### P20. ADR-022 appliqué partiellement

- §1 (`unconfigured` selon l'environnement) : non implémenté comme écrit (P4).
- §6 (nettoyer la conf morte) : appliqué à `field_mappings` seulement.

### P21. ADR-023 : un second interrupteur de fait

- L'ADR rejetait deux interrupteurs, mais `EMBEDDING_PROVIDER=noop` en est un second.
- `noop` est la valeur par défaut, alors que `ENVIRONMENT` applique « le défaut penche vers le refus ». Par défaut, on écrit donc des vecteurs nuls.

### P22. Deux notions d'environnement

- Les environnements Kedro (`conf/<env>/`, `--env`) sont désactivés par `CONFIG_LOADER_ARGS`, et remplacés par la variable `ENVIRONMENT`, arbitrée dans le code.
- **Avantage** : l'absence de la variable vaut `prod`, donc protégé.
- **Coût** : aucune surcouche de valeurs pour la prod, d'où P4.
- **À faire** : trancher explicitement ce choix dans un ADR plutôt que d'en hériter.
