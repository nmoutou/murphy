# Corrections — data

> Périmètre : `data/` (sous-module `murphy-data`). Chemins relatifs à
> `data/`. Index et ordre d'exécution : [`README.md`](README.md).
>
> **Lot exécuté le 25 septembre 2026** (DA-01 → DA-04, DA-06), non
> commité : le sous-module reste en HEAD détachée sur `8892b6b`. Il ne
> reste que DA-05, un chantier dédié.

## 1. Tableau

| ID | Point | Sévérité | Statut |
|---|---|---|---|
| DA-01 | Vestiges `src/data/{datasets,models,utils,pipelines}` : 584 lignes supprimées, qui portaient les 95 erreurs ruff | Bloquant (lint rouge) | ✅ |
| DA-02 | `src/data/settings.py` : modèle Kedro commenté et résolveur `oc.env` inutile | Dette | ✅ |
| DA-03 | `ruff format --check` : fichiers non formatés | Dette | ✅ |
| DA-04 | `uv.lock` non suivi | Dette | ✅ commité par le porteur (`8892b6b`) |
| DA-05 | 4 modules de plus de 300 lignes, dont `hooks.py` à 915 | Dette | ⏸ chantier dédié |
| DA-06 | Code mort marginal dans `ragcore` | Confort | ✅ |

## 2. Résultat

| Contrôle | Avant | Après |
|---|---|---|
| `ruff check src` | 95 erreurs | ✅ 0 |
| `ruff format --check src` | 12 fichiers | ✅ tout formaté |
| `mypy src/ragcore` (strict) | ✅ | ✅ |
| `pytest` (unitaires + golden) | 296 passés, 86 % | 294 passés (les 2 tests de `from_raw_document` sont retirés), 86 % |
| `kedro registry list` | `__default__`, `ingestion` | identique |
| paramètres chargés par `KedroSession` | — | identiques, octet pour octet |

Les tests d'intégration (`-m integration`, testcontainers) n'ont pas été
relancés. Aucun ne touche au code modifié : les tests Neo4j n'appelaient
pas `initialize()`.

## 3. Ce qui a été fait

### DA-01 — vestiges de `src/data/`

Supprimés :
- `datasets/` : datasets Kedro remplacés par les adapters `ragcore` ;
- `models/` : l'**ancien modèle de chunk à `chunkId`**, dernier témoin du
  contrat que lit encore le backend (TR-01) ;
- `utils/` ;
- `pipelines/` : un `__init__.py` vide.

Aucune référence ne subsistait dans `conf/`, `src/`, `pyproject.toml` ni
la documentation. `__init__.py` (qui porte `__version__`), `__main__.py`,
`settings.py` et `pipeline_registry.py` restent.

### DA-02 — `settings.py`

- Supprimés :
  - les blocs commentés du modèle Kedro ;
  - `custom_resolvers` (`oc.env`) et son import : aucun `${…}` dans
    `conf/` ;
  - `CONFIG_LOADER_CLASS = OmegaConfigLoader`, déjà la valeur par défaut
    de Kedro 1.1.
- **`CONFIG_LOADER_ARGS = {"base_env": "base"}` est conservé**, avec un
  commentaire. Ce n'est pas une redite : il *remplace* les arguments par
  défaut de Kedro (`base_env: "base"`, `default_run_env: "local"`). Le
  projet tourne donc aujourd'hui **sans** environnement d'exécution
  superposé. Le supprimer réactiverait `local` : c'est un changement de
  comportement, pas du nettoyage. Il n'existe pas de `conf/local/`.
- L'import tardif de `TelemetryHooks` après `structlog.configure` est
  conservé ; son `noqa: E402` est maintenant justifié en commentaire.

### DA-03 — formatage

`ruff format src` a reformaté 5 fichiers :
- `settings.py`, `__init__.py`, `__main__.py` ;
- `adapters/storage/mongo/document_repository.py` ;
- `tests/golden/test_fingerprint.py`.

Ce ne sont que des changements de mise en page : un appel replié sur une
ligne, des lignes vides, des guillemets.

### DA-06 — code mort marginal

| Élément | Décision | Fait |
|---|---|---|
| `GraphRepository.initialize()` | **supprimée** (décision du porteur) | retirée du port, de l'adapter Neo4j et du fake |
| `ELI.from_raw_document()` | supprimée | retirée, avec l'import `TYPE_CHECKING` orphelin, ses 2 tests et leur helper `_raw` |
| `count_for_owner`, `existing_node_ids`, `delete_relations_from`, `delete_relations_by_run` | **conservés** : ils font partie du contrat de compensation de la saga, et le port les documente | — |

> ⚠️ **Constat à garder pour les travaux de performance** : le graphe
> Neo4j n'a **aucun index sur `identifier`**, et n'en a jamais eu,
> puisque `initialize()` n'était appelée nulle part. Chaque
> `MERGE (… {identifier: X})` de la saga, ainsi que la ré-hydratation des
> `Pending`, parcourt donc tous les nœuds du label. Le code supprimé
> faisait
> `CREATE INDEX IF NOT EXISTS FOR (n:<label>) ON (n.identifier)` pour
> `Document`, `Article`, `Texte`, `Section` et `Pending`. Si l'ingestion
> du corpus complet ralentit avec la taille du graphe, c'est la première
> piste.

## 4. Reste à faire

### DA-05 — modules de plus de 300 lignes

`CLAUDE.md` fixe 300 lignes par fichier. Hors tests, ces modules le
dépassent :

| Fichier | Lignes |
|---|---|
| `src/ragcore/orchestration/kedro/hooks.py` | 915 |
| `src/ragcore/core/links/extraction.py` | 541 |
| `src/ragcore/sources/generic/parser.py` | 540 |
| `src/ragcore/adapters/storage/neo4j/graph_repository.py` | 352 |

Ce code est critique (télémétrie, statut de run, graphe) et bien
couvert. Le découper est un **chantier dédié**, avec lecture préalable et
plan annoncé : il n'a rien d'une tâche de nettoyage. Commencer par
`hooks.py`, trois fois au-dessus de la limite.

Six fichiers de test dépassent aussi 300 lignes (jusqu'à 501 pour
`tests/integration/test_neo4j_graph_repository.py`). Ce n'est pas une
priorité.

Pour la règle des 30 lignes par fonction : `PLR0915`
(`too-many-statements`) est déjà actif via la famille `PL`, mais avec le
seuil par défaut de Pylint, 50 instructions. Le baisser se fait avec
`[tool.ruff.lint.pylint] max-statements`.
