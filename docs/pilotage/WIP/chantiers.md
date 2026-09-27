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

## 1. Découper `hooks.py` — fait (2026-09-27)

`data/src/ragcore/orchestration/kedro/hooks.py` faisait **960 lignes**, avec un
`before_pipeline_run` de 182 lignes de code (`noqa: PLR0915`), un `_build_runner` qui
recopiait la création des clients, deux branches sur le fournisseur d'embedding, un
embedder typé `object`, et des tests qui écrivaient ses attributs privés.

| Module (`orchestration/kedro/` sauf mention) | Contenu | Lot |
|---|---|---|
| `run_parameters.py` | Lecture de `parameters.yml` et des `--params` : fonctions pures | 1 (`b099369`) |
| `application/publish_collection.py` | `CollectionPublisher` : la règle de publication (ADR-039), hors de Kedro | 2 (`433ec2c`) |
| `run_plan.py` | `RunPlan` figé : ce que le run écrit, dérivé une fois | 3 (`ccc0681`) |
| `stores.py` | `open_clients` (seule création des clients, hook et workers), dépôts | 3 |
| `assembly.py` | `prepare_embedder` (une branche), `build_processing_stack`, `build_runner` | 3 |
| `hooks.py` | Émission et clôture dédoublonnées ; l'agrégateur devient le `run_stats_sink` | 4 (`4256e41`) |
| `run_session.py` | `RunSession` : l'état du run sans `None`, `emit_lifecycle_event`, `close` | 5 |

Résultat : `hooks.py` fait 210 lignes (cycle de vie Kedro seul, deux attributs), aucun
module du dossier ne dépasse 300 lignes, aucune de leurs fonctions ne dépasse
30 lignes de code (hors `pipeline.py` et `workload.py`, chantier 3), et plus aucun
`noqa` ni `type: ignore` dans les modules du hook (reste le `noqa: PLR0913` de
`build_document_workload`, chantier 3). Les tests ne touchent plus
d'attribut privé du hook. Détail par lot dans `ameliorations.md`.

**Reste à faire, à la main** : un `kedro run --params source=cass` sur la stack `ingest`,
comparé à un bilan d'avant le chantier (statut, compteurs, collection publiée).

## 2. `except Exception` dans `data/` — fait (2026-09-27)

Onze `except Exception` dans `data/src` (hors tests). Les deux « `except:` nus » du
premier relevé étaient des faux positifs, dans des commentaires de tests. Les
`# noqa: BLE001` présents étaient sans effet : `BLE` n'était pas sélectionnée.

| Site | Issue |
|---|---|
| `core/links/extraction.py` `_identifier` | Restreint à `pydantic.ValidationError` (lot 1) |
| `sources/generic/parser.py` `_identifier` | Restreint à `pydantic.ValidationError`, import aliasé (lot 1) |
| `orchestration/kedro/hooks.py` | Extrait dans `_load_parameters`, restreint à `DatasetError` (lot 1) |
| `orchestration/kedro/nodes/compute_idempotence.py` | Restreint à `ParseError`, le contrat de `BaseParser` ; une exception hors contrat arrête le run (lot 1) |
| `sources/generic/parser.py:119`, `application/saga.py:37` | Frontières qui relancent (`raise … from exc`) : `BLE` les accepte, rien à faire |
| `application/ingestion_runner.py:139` | Frontière voulue, `noqa` justifié (lot 2) |
| `application/saga.py:64` | Frontière voulue, `noqa` justifié (lot 2) |
| `adapters/telemetry/registry_aware.py` (×3) | Frontières voulues, `noqa` justifiés (lot 2) |

Lot 1 : `bc85996`. Lot 2 : `BLE` ajoutée à `[tool.ruff.lint] select` ; la CI refuse
désormais tout nouvel `except Exception` sans relance ni `noqa` justifié. Détail dans
`ameliorations.md`.

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
2. ~~Chantier 2 : `except` (petit, et active `BLE` avant les refactors).~~ Fait.
3. ~~Chantier 1 : `hooks.py`.~~ Fait.
4. Chantier 3 : fonctions longues de `data/`.
5. Chantier 4 : backend / frontend. Indépendant des autres, il peut passer avant.
6. Chantier 5 : tests du frontend, après le lot 2 du chantier 4.
