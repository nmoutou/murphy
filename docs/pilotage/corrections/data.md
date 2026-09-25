# Corrections — data

> Périmètre : `data/` (sous-module `murphy-data`). Chemins relatifs à
> `data/`. Index et ordre d'exécution : [`README.md`](README.md).
>
> Le paquet `ragcore` est en bon état : `mypy --strict` passe, 296 tests
> unitaires et golden sont verts, avec 86 % de couverture, et
> `ruff check src/ragcore` est propre. Les points ci-dessous portent
> surtout sur la **coquille Kedro** `src/data/` et sur la taille de
> quelques fichiers.

## 1. Tableau

| ID | Point | Sévérité | Statut |
|---|---|---|---|
| DA-01 | Vestiges `src/data/{datasets,models,utils}` : environ 480 lignes mortes, porteuses des 95 erreurs ruff | Bloquant (lint rouge) | ⬜ |
| DA-02 | `src/data/settings.py` : modèle Kedro commenté et résolveur `oc.env` inutile | Dette | ⬜ |
| DA-03 | `ruff format --check` : fichiers non formatés | Dette | ⬜ |
| DA-04 | `uv.lock` non suivi | Dette | ⏸ confirmer |
| DA-05 | 4 modules de plus de 300 lignes, dont `hooks.py` à 915 | Dette | ⏸ chantier dédié |
| DA-06 | Code mort marginal dans `ragcore` | Confort | ⬜ |

## 2. Détail

### DA-01 — vestiges de `src/data/`

`CLAUDE.md` les déclare déjà « unused vestiges ». Vérifié : aucune
référence dans `conf/`, `src/`, `pyproject.toml` ni la documentation.

| Dossier | Contenu |
|---|---|
| `src/data/datasets/` | `mongodb_dataset.py`, `neo4j_dataset.py`, `qdrant_dataset.py`, `xml_source_dataset.py` : datasets Kedro remplacés par les adapters `ragcore` |
| `src/data/models/` | `data.py` : l'**ancien modèle de chunk** avec `chunkId`, dernier témoin du contrat que lit encore le backend (TR-01) |
| `src/data/utils/` | `partitioning.py`, `validation.py` |

- Supprimer les trois dossiers. Les 95 erreurs ruff du dépôt partent avec
  eux.
- `src/data/pipelines/` ne contient qu'un `__init__.py` vide :
  `pipeline_registry.py` délègue à `ragcore`. Le supprimer aussi, après
  avoir vérifié que `kedro run` et `kedro viz` démarrent sans lui.

### DA-02 — `settings.py`

- Supprimer les blocs commentés du modèle Kedro (l. 41-47, 49-50,
  64-66, 68-70) : ils redisent les valeurs par défaut de Kedro.
- Supprimer `CONFIG_LOADER_ARGS["custom_resolvers"]` et l'import
  `from omegaconf.resolvers import oc` (l. 32, 59-61). **Aucun YAML de
  `conf/` n'utilise `${oc.env:…}`** : vérifié, `conf/` ne contient aucune
  interpolation `${`. Le commentaire des l. 7-13 le constate déjà.
- Restent deux `# noqa: E402` (`TelemetryHooks`, `OmegaConfigLoader`),
  importés après `structlog.configure`. Si cet ordre n'est pas voulu, les
  remonter en tête de fichier. S'il l'est (configurer structlog avant que
  les hooks ne créent leurs loggers), l'écrire dans un commentaire au-dessus
  des imports.

### DA-03 — formatage

`ruff format --check src` signale 12 fichiers. Après DA-01, il en reste
3 :
- `src/data/settings.py` ;
- `src/ragcore/adapters/storage/mongo/document_repository.py` ;
- `src/ragcore/tests/golden/test_fingerprint.py`.

Les formater dans un **commit dédié** au formatage.

### DA-04 — `uv.lock`

`data/uv.lock` existe mais n'est pas suivi par git. `CLAUDE.md` prescrit
`uv`, et l'ingestion doit être reproductible : le fingerprint de
collection en dépend indirectement, à travers les versions du parseur et
du chunker. **Le commiter**, sauf raison contraire du porteur.

### DA-05 — modules de plus de 300 lignes

`CLAUDE.md` fixe 300 lignes par fichier. Hors tests, ces modules le
dépassent :

| Fichier | Lignes |
|---|---|
| `src/ragcore/orchestration/kedro/hooks.py` | 915 |
| `src/ragcore/core/links/extraction.py` | 541 |
| `src/ragcore/sources/generic/parser.py` | 540 |
| `src/ragcore/adapters/storage/neo4j/graph_repository.py` | 362 |

Ce code est critique (télémétrie, statut de run, graphe) et bien
couvert. Le découper est un **chantier dédié**, avec lecture préalable et
plan annoncé : il n'a rien d'une tâche de nettoyage. Commencer par
`hooks.py`, trois fois au-dessus de la limite.

Six fichiers de test dépassent aussi 300 lignes (jusqu'à 501 pour
`tests/integration/test_neo4j_graph_repository.py`). Ce n'est pas une
priorité.

Pour mesurer aussi la règle des 30 lignes par fonction, activer
`PLR0915` (`too-many-statements`) dans `[tool.ruff.lint]`.

### DA-06 — code mort marginal

Candidats remontés par `vulture` et vérifiés un par un. La plupart des
signalements de `vulture` sont des faux positifs : champs pydantic,
`model_config`, validateurs.

| Élément | Constat | Proposition |
|---|---|---|
| `GraphRepository.initialize()` | déclarée sur le port (`core/ports/graph_repository.py:32`), l'adapter et le fake, **jamais appelée** | supprimer des trois, ou l'appeler dans `connect` si elle pose des contraintes Neo4j utiles |
| `ELI.from_raw_document()` | `core/models/identifiers.py:55` : seuls ses propres tests l'appellent | supprimer avec ses tests |
| `count_for_owner`, `existing_node_ids`, `delete_relations_from`, `delete_relations_by_run` | seuls les tests d'intégration les appellent | **conserver** : ils font partie du contrat de compensation de la saga, et le port les documente |
