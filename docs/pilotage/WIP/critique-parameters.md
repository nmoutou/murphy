# Critique de `data/conf/base/ingestion/parameters.yml`

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

- **Lues** : `chunking`, `embedding`, `embedding_runtime.enabled`, `exportation.unconfigured`, `exportation.neo4j.*`, `maintenance.cache_paths`, `maintenance.nuke_all`.
- **Non lues** : `nlp`, `importation`, `formatting`, `embedding_runtime.embedding_service_timeout`, `embedding_runtime.batch_size`, `exportation.mongodb`, `exportation.qdrant`, `maintenance.cleanup_enabled`.

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

### P3. `cache_paths` ne vide rien, en silence

- **Constat** : les chemins sont relatifs au répertoire courant. Lancé depuis `data/`, le run vise `data/data/cache` et `data/data/meta/events`, qui n'existent pas. `_clear` renvoie 0. Les événements sont en réalité dans `data/08_reporting/events` (`META_JSONL_DIR`).
- **Contradictions** :
  - C'est le piège du chemin relatif dénoncé pour `XML_SOURCE_PATH`.
  - Corrigé, `cleanup` effacerait la télémétrie, alors que `nuke_all` s'interdit de toucher `MURPHY_META`.
  - `cleanup_enabled` n'est pas lu : impossible de désactiver le nettoyage.
- **Piste** : décider ce que « cache » désigne. Si rien : supprimer `cleanup`. Sinon : chemin absolu, et échec si le chemin est absent.

### P4. `unconfigured` échappe à `ENVIRONMENT`

- **Constat** : ADR-022 §1 prévoit ingestion en dev, exclusion en prod. Les trois autres réglages propres au dev sont arbitrés par l'environnement, pas celui-ci.
- **Conséquence** : un seul fichier de paramètres, sans surcouche par environnement, donc **la prod ingère les balises non configurées**.
- **Piste** : arbitrer par `ENVIRONMENT`, comme les autres (voir P11).

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
| `maintenance.cleanup_enabled` | Non lu. | Trancher avec P3 |

**Conclusion** : les faits propres à une source (balises, titres, liens, verbes) ont été déplacés à bon escient dans les tables par source. Le YAML ne devrait contenir que ce qu'un opérateur change d'un run à l'autre.

### P6. Pourquoi ces clés ont survécu

- Seuls `chunking` et `embedding` refusent les clés inconnues (`extra="forbid"`).
- Partout ailleurs, une clé inconnue ou mal orthographiée passe en silence.

---

## C. Rangement

### P7. Fichier unique dans un sous-dossier

- `ingestion/` est un vestige de la partition d'ADR-026. ADR-042 a supprimé `workflow/` sans défaire la partition.
- Tout `data/` est de l'ingestion : ce nom ne distingue rien.
- **Piste** : `conf/base/parameters.yml`.

### P8. Des « phases » sans rapport avec le pipeline

- Numérotation 1, 3, 3 bis, 4, 5 : pas de phase 2.
- Pipeline réel : cleanup → nukeAll → connect → computeIdempotence → ingest → resolveRelations → report. La maintenance, numérotée « phase 5 », s'exécute en premier.
- Le code appelle déjà « phase 1 / phase 2 » l'ingestion et la résolution des relations : deux numérotations entrent en conflit.
- Détails : « PARAMÈTRE GÉNÉRAUX » (faute d'accord), casse irrégulière des titres.

### P9. `exportation` est un fourre-tout

| Clé | Relève en réalité de |
|---|---|
| `unconfigured` | le parsing |
| `neo4j.labels` | le modèle de données |
| `neo4j.include_*` | le régime dev |

### P10. `embedding` / `embedding_runtime` : séparation sans objet

- La séparation « quoi / comment » servait l'empreinte d'ADR-026, qui a été supprimée.
- `embedding_runtime` n'a plus qu'une clé lue, `enabled`, qui est un choix de régime dev, pas un réglage de transport.
- Le « comment » vit en réalité dans l'environnement (`EmbeddingRuntimeSettings`) : même notion, deux emplacements.

### P11. Réglages propres au dev éparpillés

- Quatre réglages (`nuke_all`, `embedding_runtime.enabled`, `neo4j.include_*`, `unconfigured`) dans trois blocs.
- `docs/technical/data/reference/configuration.md` regroupe déjà les trois premiers dans un tableau « garde-fous dev/prod ».
- **Piste** : un bloc `dev:` unique, ignoré hors dev. C'est l'argument d'ADR-026 : une frontière portée par la structure, pas par des commentaires.

### P12. Le format du YAML est connu en plusieurs endroits

- `run_parameters.py` affirme être « le seul endroit qui connaisse la forme du YAML ». C'est faux : `pipeline.py`, `nuke_all.py` et `compute_idempotence.py` la connaissent aussi.
- Les nœuds reçoivent des blocs entiers (`params:exportation`, `params:maintenance`) pour n'en lire qu'une clé.
- `nuke_all` relit `ENVIRONMENT` lui-même au lieu de passer par le `RunPlan`.

---

## D. Valeurs et nommage

### P13. `chunking`

- L'unité n'apparaît pas dans le nom, alors que le code parle de `max_chunk_size`.
- La règle `overlap < size`, annoncée par la doc, n'est pas validée.
- `overlap: 25` n'est pas justifié (environ 8 tokens, 6,5 %), contrairement à `size`.

### P14. `embedding`

- `model_name` fait doublon avec `EMBEDDING_MODEL` (`.env.dev`, qui sert à TEI et au backend). La docstring de `ROOT_ENV_FILE` affirme « ils ne sont plus deux variables » : c'est faux.
- Le risque est seulement atténué par la vérification `GET /info` au démarrage.
- `dimension` est une propriété du modèle, donc redondante : elle pourrait être mesurée au démarrage plutôt que déclarée.

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

### P17. Commentaires décalés

- « À NE PAS activer en prod » : `nuke_all` est de toute façon refusé hors dev. Le commentaire devrait décrire ce refus.
- Rien n'indique l'unité de `embedding_service_timeout`.

---

## E. Validation

### P18. Trois stratégies de validation coexistent

| Stratégie | Blocs |
|---|---|
| Pydantic strict | `chunking`, `embedding` |
| Validation écrite à la main | `labels`, `unconfigured` |
| `.get()` avec défaut, puis `bool()` | tout le reste |

**Piste** : un modèle pydantic unique pour tout le fichier (`extra="forbid"`, booléens stricts), validé dans `plan_run`. Les nœuds reçoivent un plan typé au lieu de dictionnaires bruts. Cela règle P1, P2, P6 et P12.

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
