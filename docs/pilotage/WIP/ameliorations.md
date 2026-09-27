# Améliorations de qualité

Journal des améliorations faites et des pistes écartées. Une amélioration listée ici
n'est pas refaite. Les lots précédents (BE-01…18, FE-01…11, TR-01…07, DA-01…06) sont
dans l'historique git : `git show 9c32a83^:docs/pilotage/corrections/`.

## Faites

### 2026-09-27 — `hooks.py` : paramètres du run extraits (chantier 1, lot 1)

- **Fichiers** : `orchestration/kedro/hooks.py`, nouveau `orchestration/kedro/run_parameters.py`
  (sous `data/src/ragcore/`) ; imports de `test_load_parameters.py`,
  `test_resolve_sources.py`, `golden/test_fingerprint.py` ; deux docstrings qui citaient
  les anciens noms (`compute_idempotence.py`, `graph_repository.py`) ;
  `docs/technical/data/reference/pipeline.md` et `configuration.md`.
- **Catégorie** : structure (taille de fichier).
- **Fait** : déplacement pur de `load_parameters`, `build_workflow_config`,
  `resolve_embedding_enabled`, `resolve_node_hydration` et `resolve_sources`, devenues
  publiques (sans `_`) puisqu'importées d'ailleurs. Code et docstrings inchangés.
- **Pourquoi** : premier des 4 lots qui ramènent `hooks.py` (960 lignes) sous 300 ; ces
  fonctions pures sur `params` n'ont rien à voir avec le cycle de vie du run.
- **Vérification** : `ruff`, `ruff format --check`, `mypy` verts ; 313 tests réussis,
  dont le cliquet `golden/test_fingerprint.py` (collection dérivée inchangée) ;
  `deepcopy` des `HOOKS` de `data/settings.py` OK. `hooks.py` : 960 → 801 lignes.

### 2026-09-27 — `data/` : règle ruff `BLE` activée (chantier 2, lot 2)

- **Fichiers** : `data/pyproject.toml`, `adapters/telemetry/registry_aware.py`,
  `application/saga.py`, `application/ingestion_runner.py` (sous `data/src/ragcore/`),
  `docs/pilotage/WIP/chantiers.md`.
- **Catégorie** : gestion d'erreurs / outillage.
- **Fait** : `"BLE"` (flake8-blind-except) ajouté à `[tool.ruff.lint] select`. Les
  5 frontières voulues portent un `# noqa: BLE001 — <raison>` : les 3 de la télémétrie
  (une panne de backend ne casse pas le run, elle est comptée), la compensation de la
  saga (un échec n'interrompt pas les suivantes) et le runner (le document est perdu,
  pas le run).
- **Pourquoi** : sans la règle, rien n'empêchait un nouvel `except Exception` aveugle ;
  les `noqa: BLE001` existants étaient sans effet.
- **Vérification** : `ruff check .` vert ; un `except Exception: pass` d'essai est
  refusé (`BLE001`, code de sortie 1) puis retiré. `ruff format --check`, `mypy` verts ;
  313 tests réussis.

### 2026-09-27 — `data/` : 4 `except Exception` restreints (chantier 2, lot 1)

- **Fichiers** : `core/links/extraction.py`, `sources/generic/parser.py`,
  `orchestration/kedro/hooks.py`, `orchestration/kedro/nodes/compute_idempotence.py`,
  `core/exceptions.py` (commentaire) ; tests : `sources/legi/tests/test_relations.py`,
  `sources/legi/tests/test_parser.py`, `tests/unit/core/test_exceptions.py`
  (docstring), nouveaux `tests/unit/orchestration/test_load_parameters.py` et
  `test_compute_idempotence.py` (chemins relatifs à `data/src/ragcore/`).
- **Catégorie** : gestion d'erreurs.
- **Fait** :
  - `extraction._identifier` : `except pydantic.ValidationError`. Seul un id mal formé
    est déclaré `identifiant` inconnu ; un bug de `identifier_for` remonte.
  - `GenericParser._identifier` : `except PydanticValidationError` (import aliasé, le nom
    est pris par l'erreur métier) relayé en `ValidationError` métier ; le
    `except ValidationError: raise` devenu inutile disparaît. Un bug de la table devient
    une `ParseError` via la frontière de `parse`, plus un refus métier.
  - `hooks.py` : le chargement de `parameters.yml` passe dans `_load_parameters`, qui ne
    traduit que la `DatasetError` de Kedro. Testable sans `.env.dev` ; prépare le
    chantier 1.
  - `compute_idempotence_node` : `except ParseError`, le contrat de `BaseParser`.
    **Changement de comportement** : une exception hors contrat (le `ValueError` de
    `RoutingParser` pour un document non routable) arrête le run au lieu d'exclure le
    document en `parse_error`. C'est ce qu'annonçait la docstring de
    `composite._unroutable` (« il faut le savoir tout de suite »).
- **Pourquoi** : ces captures déguisaient des bugs en cas prévus (id illisible, refus
  métier, config illisible, document illisible).
- **Vérification** : 7 nouveaux tests, dont 4 qui échouaient avant le correctif
  (vérifié). `ruff`, `ruff format --check`, `mypy` verts ; 313 tests réussis.
  `ruff --select BLE` ne signale plus que les 4 frontières voulues.

### 2026-09-27 — `data/` vérifié en CI

- **Fichiers** : `.github/workflows/ci.yml`, `CLAUDE.md`, `data/README.md`,
  `docs/pilotage/WIP/chantiers.md` ; suppression de `data/lab/` (2 notebooks).
- **Catégorie** : CI / filet de sécurité.
- **Fait** : nouveau job `python` (« Python (data) »), en parallèle de `typescript`.
  `astral-sh/setup-uv` épinglé par SHA (v10.2.0), uv 0.10.7 et Python 3.13 comme en
  local, cache sur `data/uv.lock`. `uv sync --locked --extra dev` échoue si `uv.lock` ne
  suit plus `pyproject.toml` ; puis `ruff check .`, `ruff format --check .`, `mypy`
  (strict, `src/ragcore`) et `pytest` (tests unitaires ; `integration` exclu par
  `addopts`). Aucun `.env.dev` ni aucune base n'est nécessaire.
- **Pourquoi** : rien ne vérifiait `data/`, alors que les chantiers 1 à 3 vont le
  refactorer. `ruff format --check .` échouait sur les notebooks de `data/lab/`,
  supprimés à cette occasion.
- **Vérification** : le job simulé sur un clone propre (sans `.venv`, `.env.dev` ni
  `conf/local`) : ruff 0 erreur, 189 fichiers formatés, mypy 0 erreur sur 127 fichiers,
  306 tests réussis (34 d'intégration désélectionnés), couverture 86 %.

### 2026-09-26 — `/completions` soumis au budget de stream par IP

- **Fichiers** : `backend/src/routes/chat.ts`, `backend/src/middleware/streamRateLimiter.ts`,
  `backend/src/__tests__/middleware/streamRateLimiter.test.ts`,
  `docs/technical/backend/ARCHITECTURE.md`, `CLAUDE.md`.
- **Catégorie** : sécurité / coût (limitation de débit).
- **Fait** : `POST /api/v1/chat/completions` passe par `streamRateLimiter`, comme
  `/streams`. Les trois transports du chat (SSE, JSON, WebSocket) tirent sur le même
  budget par IP (10/min par défaut). Un test vérifie qu'une fois le budget épuisé par
  `/streams`, `/completions` répond 429 `STREAM_RATE_LIMIT_EXCEEDED` ; il échoue sans le
  correctif (400).
- **Pourquoi** : `/completions` exécute tout le pipeline (TEI, Qdrant, Mongo, puis le LLM
  payant) mais n'était couvert que par le limiteur global (100 requêtes / 15 min, sans
  limite de rafale). Un client pouvait donc lancer 100 générations d'un coup, en plus de
  son budget de stream sur `/streams` et le WebSocket. Changement d'une ligne, sans effet
  sur le frontend, qui n'utilise que le WebSocket.
- **Vérification** : `npm run check` vert avant et après (backend : 17 suites, 115 puis
  116 tests).

## Pistes écartées

- **Tests du frontend** (aucun runner aujourd'hui) : forte valeur, mais installer un
  runner (Vitest + Testing Library) touche la config, les dépendances et la CI ; à
  traiter comme un chantier dédié.
- **`readLines` (`infra/llm.ts`) perd une dernière ligne sans saut de ligne final** :
  comportement documenté ; le SSE termine chaque événement par une ligne vide, donc sans
  effet avec un fournisseur conforme.
