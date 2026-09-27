# Chantiers de qualité

Plan des chantiers de qualité, du plus rentable au moins urgent. Chaque chantier se
découpe en **lots** : un lot = une amélioration, `npm run check` (ou `ruff` / `mypy` /
`pytest` pour `data/`) vert avant et après, une entrée dans `ameliorations.md`, un
commit. Un lot qui toucherait plus de 3 fichiers en cascade est présenté avant d'être
fait.

Relevé du 2026-09-26. Les longueurs de fonction sont comptées **hors lignes vides,
commentaires et docstrings** (règle du `CLAUDE.md`) ; les longueurs de fichier, elles,
sont brutes.

## Prérequis : `data/` en CI — fait (2026-09-27)

- **Constat** : `.github/workflows/ci.yml` ne lançait que `npm run check` et le build
  Docker. Ni `ruff`, ni `mypy`, ni `pytest` ne tournaient sur `data/`.
- **Fait** : un job `python` dans `ci.yml` (`working-directory: data`, uv 0.10.7,
  Python 3.13) : `uv sync --locked --extra dev`, puis `ruff check .`,
  `ruff format --check .`, `mypy` (cible `src/ragcore` via `[tool.mypy] files`) et
  `pytest` (`addopts` exclut `integration`). Les tests `integration` (testcontainers)
  restent hors CI. Détail dans `ameliorations.md`.
- **Pourquoi d'abord** : les chantiers 1 à 3 refactorent `data/`. Sans ce filet, une
  régression passerait inaperçue jusqu'au prochain `kedro run`.

## 1. Découper `hooks.py`

`data/src/ragcore/orchestration/kedro/hooks.py` : **949 lignes** (568 de code), trois
fois la limite.

### Constat

- `TelemetryHooks.before_pipeline_run` fait **182 lignes de code**. Il enchaîne au moins
  douze responsabilités : charger `parameters.yml`, dériver la collection, ouvrir le
  tracker, vérifier que TEI sert le bon modèle, créer les clients Mongo / Neo4j / Qdrant,
  poser les index, instancier six dépôts, résoudre les sources et le contexte, monter la
  pile de télémétrie, assembler connecteur / parser / chunker / extracteur, choisir
  l'embedder, construire le runner et le service de résolution, puis faire douze
  `catalog.save`. Un `# noqa: PLR0915` le justifie comme « pur câblage ».
- `_build_runner` fait 63 lignes et recrée, pour chaque worker, les mêmes trois clients
  que `before_pipeline_run`, avec le même code.
- **Le choix de l'embedder est écrit deux fois** : une première branche sur
  `embedding_settings.provider` pour vérifier le modèle servi (l. 223-230), une seconde
  pour instancier l'embedder (l. 393-398).
- **Un trou de typage** : `self._embedder: object | None`, puis `getattr(self._embedder,
  "truncations", 0)`. Le port `core/ports/embedder.py` existe mais n'est pas utilisé.
- La classe mêle trois domaines : l'assemblage du run, le cycle de vie du run (bilan,
  drain, tracker) et la **publication du pointeur de collection** (ADR-039), qui est une
  règle métier.
- Les tests sont couplés aux attributs privés : `test_publish_condition.py` et
  `test_summary_absorbs_workers.py` écrivent directement `hooks._published_repo`,
  `hooks._qdrant_collection`, `hooks._is_full_run` et `hooks._aggregator`.

### Découpage proposé

| Nouveau module (`orchestration/kedro/`) | Contenu | Origine |
|---|---|---|
| `run_parameters.py` | `build_workflow_config`, `resolve_embedding_enabled`, `resolve_node_hydration`, `resolve_sources` : fonctions pures sur `params` | l. 820-949 |
| `assembly.py` | La racine de composition : `build_embedder` (une seule branche sur le fournisseur), `build_stores` (clients + dépôts, réutilisé par les workers), `build_source_stack`, `build_runner`. Rend une dataclass figée `IngestionAssembly` dont les champs sont les entrées du catalogue | `before_pipeline_run`, `_build_runner` |
| `publication.py` | `publish_if_complete(...)` : la condition de publication (statut `ok` + `may_publish`) comme fonction, testable sans instancier les hooks | `_publish_collection`, `_contract_allows_publication` |
| `hooks.py` | Le cycle de vie Kedro seul : `before_pipeline_run` appelle `assembly` puis sauve dans le catalogue ; `after_pipeline_run` / `on_pipeline_error` ; `absorb`, drain, bilan, tracker | ce qui reste |

### Lots

1. Extraire `run_parameters.py` (déplacement pur ; mettre à jour les imports de
   `test_resolve_sources.py` et `golden/test_fingerprint.py`).
2. Extraire `publication.py` et réécrire `test_publish_condition.py` contre la fonction
   plutôt que contre les attributs privés.
3. Extraire `assembly.py` : dédoublonner le choix de l'embedder et la création des
   clients, typer l'embedder par son port, retirer le `noqa: PLR0915`.
4. Relire `hooks.py` restant, qui devrait passer sous 300 lignes, et
   `test_summary_absorbs_workers.py`.

### Points d'attention

- `settings.py` instancie `TelemetryHooks()` à l'import et Kedro le `deepcopy`. Rien
  d'allouant ne doit remonter dans `__init__`. La docstring de `_runtime` explique le
  piège.
- Les longs commentaires de justification (fail-fast, ADR-039, mesures de perf de
  `_WORKER_COUNT`) suivent le code qu'ils justifient. On ne les supprime pas.
- **Vérification** : `pytest` unitaire, puis un `kedro run --params source=cass` sur la
  stack `ingest`, pour comparer le bilan (statut, compteurs, collection publiée) avant et
  après.
- **Taille** : 4 lots, environ 8 fichiers. Le plan détaillé du lot 3 est à valider avant
  de le lancer.

## 2. `except Exception` dans `data/`

### Constat

Onze `except Exception` dans le code de `data/src` (hors tests). Les deux « `except:`
nus » du premier relevé étaient des **faux positifs**, dans des commentaires de tests.
Autre constat : les `# noqa: BLE001` présents sont **sans effet**. La règle `BLE`
(flake8-blind-except) n'est pas sélectionnée dans `pyproject.toml`, donc ruff ne vérifie
rien de ce côté.

| Site | Verdict | Action |
|---|---|---|
| `core/links/extraction.py:519` (`table.identifier_for`) | À préciser : `identifier_for` (LEGI, JURI) ne lève que la `ValidationError` de pydantic | `except pydantic.ValidationError` |
| `sources/generic/parser.py:234` (`_build_identifier`) | À préciser, même raison. Attention au conflit de noms avec la `ValidationError` métier du projet | idem, import aliasé |
| `orchestration/kedro/hooks.py:179` (`catalog.load("parameters")`) | À préciser : Kedro lève `DatasetError` | `except DatasetError` |
| `orchestration/kedro/nodes/compute_idempotence.py:127` | À examiner : « autre erreur de parsing » après `except ValidationError` ; le parser relaie déjà tout en `ParseError` (`parser.py:119`) | `except ParseError` si le contrat du port le garantit |
| `sources/generic/parser.py:119` | Frontière du parser : toute panne devient `ParseError`, chaînée | garder, justifier en `noqa` |
| `application/ingestion_runner.py:139` | Frontière voulue : « le document est perdu, pas le run » | garder |
| `application/saga.py:37` et `:64` | Frontière voulue : toute panne d'une étape déclenche la compensation | garder, justifier |
| `adapters/telemetry/registry_aware.py:85`, `:102`, `:147` | Frontière voulue : une panne de télémétrie ne doit pas casser le run | garder, justifier |

### Lots

1. Ajouter `BLE` à `[tool.ruff.lint] select`. Ruff signale alors 5 sites ; chaque frontière
   voulue reçoit un `# noqa: BLE001 — <raison>`, comme le reste du code.
2. Préciser les quatre sites « à préciser » ou « à examiner », avec pour chacun un test
   qui prouve qu'une exception inattendue n'est plus avalée.

**Taille** : 2 lots, environ 7 fichiers.

## 3. Fonctions trop longues de `data/`

### Constat

Mon premier relevé visait les fichiers de plus de 300 lignes. La mesure fine montre
autre chose : `extraction.py` (541 lignes, 267 de code), `parser.py` (540 / 288) et
`graph_repository.py` (352 / 162) dépassent **à cause de leur documentation**, pas de
leur code. Le vrai problème, ce sont les **22 fonctions de plus de 30 lignes de code**.
Hors `hooks.py` (chantier 1), les plus longues :

| Lignes | Fonction |
|---|---|
| 115 | `orchestration/kedro/nodes/compute_idempotence.py` : `compute_idempotence_node` |
| 84 | `orchestration/kedro/pipeline.py` : `create_ingestion_pipeline` |
| 67 | `core/links/extraction.py` : `_version_chain` |
| 65 | `application/saga.py` : `SagaExecutor.execute` |
| 55 | `application/ingest_document.py` : `IngestDocumentUseCase.execute` |
| 55 | `adapters/storage/mongo/schemas.py` : `ensure_meta_indexes` |
| 44 | `orchestration/kedro/nodes/nuke_all.py` : `nuke_all_node` |
| 43 | `sources/generic/parser.py` : `_references` (complexité cyclomatique 12) |
| 43 | `core/links/extraction.py` : `_from_reference` |
| 42 | `application/resolve_relations.py` : `ResolveRelationsService.execute` |
| 30-40 | `_run_shard`, `_promote`, `cleanup_node`, `build_document_workload`, `merge_document_node`, `compensate_document_node`, `parse`, `_route_values`, `connect_node`, `extract_links` |

À cela s'ajoutent **14 fonctions à plus de 4 paramètres** : 10 déjà justifiées par un
`noqa: PLR0913` (au seuil de 5 de ruff), 4 de plus au seuil de 4 fixé par le
`CLAUDE.md`.

### Approche

- **Par fonction, pas par fichier.** Découper un fichier trop documenté éparpillerait sa
  documentation sans rien simplifier. On extrait les étapes nommées des longues
  fonctions ; les fichiers repasseront peut-être sous 300 lignes, sinon on tranchera
  fichier par fichier.
- Priorité à la logique métier : `compute_idempotence_node` (les branches de rejet
  « invalidé » et « erreur de parsing » répètent le même bloc télémétrie + manifeste
  `EXCLUDED`), `_version_chain`, `_from_reference`, `_references`, `saga.execute`
  (séparer l'exécution de la compensation).
- **Exceptions assumées** : `create_ingestion_pipeline` et `ensure_meta_indexes` sont des
  déclarations (liste de nœuds, liste d'index). On les découpe seulement si cela se lit
  mieux. Les nœuds Kedro gardent leurs paramètres : Kedro les câble par nom, un objet
  unique les cacherait au DAG, comme le disent déjà les `noqa`.
- **Verrou** : une fois la liste épuisée, activer `C901` et `lint.pylint.max-args = 4`
  dans `pyproject.toml`, pour que ruff tienne la règle.

**Taille** : 1 lot par fonction ou par petit groupe, environ 10 lots.

## 4. Backend et frontend : derniers écarts, puis verrou ESLint

### Constat

Le premier relevé était trop pessimiste. Les « 2 `any` et 3 `as` » étaient presque tous
des mots dans des commentaires. Mesure par le compilateur TypeScript :

- **Backend** : aucune fonction au-delà de 30 lignes, aucune imbrication au-delà de 3
  niveaux, aucun fichier au-delà de 300 lignes (le plus long est `config.ts`, 232).
- **Une seule assertion `as`** : `backend/src/validation/chatRequest.ts:51`
  (`checkedMessages as AppUIMessage[]`). Seuls le rôle et les `parts` sont vérifiés ; le
  reste de la forme du message est supposé.
- **Frontend** : trois composants dépassent 30 lignes, `ChatBox` (53), `Modal` (38) et
  `MainPanel` (31). Aucun ne dépasse 200 lignes.
- **Aucune de ces règles n'est outillée** : les configs ESLint (`backend/`, `frontend/`)
  n'activent ni `max-lines`, ni `max-lines-per-function`, ni `max-depth`, ni
  `max-params`, ni `no-magic-numbers`. La conformité actuelle ne tient qu'à la vigilance.

### Lots

1. **Supprimer le `as`** : valider les messages avec `safeValidateUIMessages` de l'AI
   SDK (v6, déjà installé), en lui passant les `dataPartSchemas` et le
   `messageMetadataSchema` de `@murphy/contract/messages`. La validation à la frontière
   devient complète, sans assertion. Point d'attention : la fonction est asynchrone, donc
   `parseChatRequest` et ses deux appelants (HTTP, WebSocket) changent de signature.
2. **Découper `ChatBox`** : sortir la logique du formulaire dans un hook et ne garder que
   le JSX. Relire `Modal` et `MainPanel`, où quelques lignes de plus en JSX peuvent être
   acceptables.
3. **Verrouiller** : ajouter aux deux configs ESLint `max-lines` (300 ; 200 pour les
   `.tsx`), `max-lines-per-function` (30, sans lignes vides ni commentaires),
   `max-depth` (3) et `max-params` (4). Les tests peuvent en être exemptés. Pour
   `no-magic-numbers`, mesurer d'abord : si le bruit est trop fort, garder le relevé
   manuel.

**Taille** : 3 lots, environ 8 fichiers.

## 5. Tests du frontend

### Constat

Aucun runner de test dans `frontend/`. Le journal (`ameliorations.md`) l'avait écarté
comme « chantier dédié ». Le contrat de stream est validé par zod des deux côtés, mais la
logique propre au frontend n'est vérifiée par rien.

### Cibles, par valeur

1. `lib/webSocketChatTransport.ts` (83 lignes) : la logique la plus risquée (fermeture du
   socket, parties terminales, abort). Testable avec un faux `WebSocket`, sans DOM.
2. `components/chat/ErrorDialog.tsx` : la lecture d'un `ChatError` (`{ stage, code }`) et
   le nom de l'étape affiché (ADR-041), y compris sur un `errorText` malformé.
3. `hooks/useRagChat.ts` : le branchement du transport et des schémas dans `useChat`.
4. `ChatBox` : envoi, champ vide, état « en cours ». Plus simple une fois le hook extrait
   (chantier 4, lot 2).

### Lots

1. Installer Vitest + Testing Library + jsdom dans `frontend/` (`vitest.config.ts`, alias
   `@/*`), ajouter `npm test -w frontend` à `npm run check`, donc à la CI. Premier test :
   le transport.
2. Un lot par cible suivante.

**Points d'attention** : la version de Vitest doit être compatible avec React 19, et
Vitest ne doit pas passer par le build Next. Ne pas fixer de seuil de couverture tant
qu'il n'y a que quelques tests.

**Taille** : 1 lot d'installation (config, dépendances, `package-lock.json`, CI), puis 3
lots de tests.

## Ordre proposé

1. ~~Prérequis : `data/` en CI.~~ Fait.
2. Chantier 2 : `except` (petit, et active `BLE` avant les refactors).
3. Chantier 1 : `hooks.py`.
4. Chantier 3 : fonctions longues de `data/`.
5. Chantier 4 : backend / frontend. Indépendant des autres, il peut passer avant.
6. Chantier 5 : tests du frontend, après le lot 2 du chantier 4.
