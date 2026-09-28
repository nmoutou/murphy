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

## 3. Fonctions trop longues de `data/` — fait (2026-09-27)

Relevé de départ (`data/src`, hors tests) : **20 fonctions de plus de 30 lignes de
code** (dont `compute_idempotence_node` à 115, `create_ingestion_pipeline` à 84,
`_version_chain` à 67, `SagaExecutor.execute` à 65), **3 fichiers de plus de 300 lignes**
(`extraction.py` 544, `parser.py` 540, `graph_repository.py` 352), une fonction au-dessus
du seuil de complexité (`parser._references`, C901 = 12) et 14 fonctions à plus de
4 paramètres.

| Lot | Commit | Périmètre |
|---|---|---|
| 1 | `38ea6be` | `application/` : saga, ingestion d'un document (`IngestionStores`), résolution, runner |
| 2 | `3a76c67` | `core/links/` : `versions.py`, `subject.py` (`LinkSubject`), `table.py`, `citations.py` ; `extract_links` à 4 paramètres |
| 3 | `3f73b5a` | `sources/generic/` : `tree.py`, `structure.py`, `unconfigured.py` ; `_chunk` via `_Span` |
| 4 | `e688090` | adaptateurs : `neo4j/node_properties.py`, index Mongo déclaratifs, `OpenAIEmbedder(EmbeddingConfig, EmbeddingTransport)` |
| 5 | `01b0c67` | `orchestration/kedro/` : nœuds, pipeline (une fonction par nœud), `WorkloadSteps`, `served_model.py` |
| 6 | `5c03fd5` | verrou ruff : `C901` (complexité ≤ 10), `max-args = 4` |

**Résultat** : 0 fonction de plus de 30 lignes, 0 fichier de plus de 300 lignes,
0 fonction au-dessus de la complexité 10 dans `data/src` hors tests. Ruff refuse
désormais toute fonction à plus de 4 paramètres, sauf les exceptions assumées :

- les nœuds Kedro (`per-file-ignores` sur `orchestration/kedro/nodes/*.py`) : leur
  signature est le DAG ;
- trois façades dont les paramètres nommés sont les champs assemblés, avec leur `noqa`
  justifié : `build_event`, `RunSummary.of`, `WorkerTelemetryFactory.__init__`.

La longueur des fonctions et des fichiers n'est pas verrouillée par un outil (décision
du 2026-09-27) : elle reste une convention du CLAUDE.md, à remesurer à chaque chantier.

**Reste à faire, à la main** : un `kedro run --params source=cass` comparé à un bilan
d'avant les chantiers 1 et 3 (statut, compteurs, nombre d'arêtes).

## 4. Backend et frontend : derniers écarts, puis verrou ESLint — fait (2026-09-28)

Relevé de départ, mesuré avec ESLint : aucun écart de taille dans le backend ; une
assertion `as AppUIMessage[]` à la frontière (`validation/chatRequest.ts`), qui ne
vérifiait que le rôle et les `parts` ; trois composants du frontend au-delà de 30 lignes
(`ChatBox` 53, `Modal` 38, `MainPanel` 31) ; 10 nombres magiques (6 codes HTTP dans le
backend, 4 dans le frontend). Aucune de ces règles n'était outillée.

| Lot | Commit | Périmètre |
|---|---|---|
| 1 | `83b5c5c` | `parseChatRequest` via `safeValidateUIMessages` (schémas `data-*` et métadonnées du contrat), sans `as` |
| 2 | `f8210ad` | `ChatBox` (`useChatInput`, `ChatBoxAttach`, `ChatBoxAction`), `Modal` (`useModalDialog`), `MainPanel` |
| 3 | `cb39648` | verrou ESLint dans les deux projets ; `backend/src/utils/httpStatus.ts` ; nombres nommés du frontend |

**Résultat** : les deux configs ESLint refusent désormais un fichier de plus de
300 lignes (200 pour un `.tsx`), une fonction de plus de 30 lignes (hors lignes vides et
commentaires), une imbrication au-delà de 3, plus de 4 paramètres, une complexité
au-delà de 10 et les nombres magiques. Les tests sont exemptés de la longueur de fonction
(un `describe` est une liste de cas) et des nombres magiques. `npm run check`, donc la
CI, applique ces règles.

Deux pièges de l'AI SDK relevés au lot 1 : le schéma de métadonnées s'applique aussi aux
messages `user` (qui n'en ont pas : le backend le rend `.optional()`), et le message
d'une `TypeValidationError` recopie toute la valeur reçue (les erreurs sont reconstruites
depuis les issues zod).

**Reste à faire, à la main** :
- sur la stack `serve`, deux questions de suite : la seconde renvoie la première réponse
  et ses sources, qui doivent passer la validation ;
- à l'écran, vérifier que rien n'a bougé : accueil puis champ ancré en bas, Entrée,
  champ vide, Annuler pendant le stream, modale d'erreur fermée par Échap ou « Fermer ».

## 5. Tests du frontend — en cours

Relevé de départ : aucun runner de test dans `frontend/`. Le contrat de stream est
validé par zod des deux côtés, mais la logique propre au frontend (transport WebSocket,
lecture des erreurs de l'ADR-041, retrait de la bulle d'une réponse échouée, saisie)
n'était vérifiée par rien.

Outillage : Vitest 5 (sur Vite, hors du build Next), Testing Library, jsdom 29. Tests
dans `frontend/src/__tests__/`, qui reprend l'arborescence de `src/`, comme dans le
backend. Pas de seuil de couverture tant qu'il n'y a que quelques tests.

| Lot | Commit | Périmètre |
|---|---|---|
| 1 | `f0124f0` | installation, `npm test -w frontend` dans `check` ; `FakeWebSocket` ; transport WebSocket et `getChatSocketUrl` |
| 2 | — | `readErrorStage` et `ErrorDialog` (ADR-041), modale fermée par Échap ou « Fermer » |
| 3 | | `useRagChat` : transport et schémas dans `useChat`, bulle retirée sur erreur |
| 4 | | `ChatBox` : envoi, champ vide, Annuler pendant le stream |

Chaque lot prouve que ses tests mordent : une mutation d'un comportement clé les fait
échouer, puis elle est annulée.

## Ordre proposé

1. ~~Prérequis : `data/` en CI.~~ Fait.
2. ~~Chantier 2 : `except` (petit, et active `BLE` avant les refactors).~~ Fait.
3. ~~Chantier 1 : `hooks.py`.~~ Fait.
4. ~~Chantier 3 : fonctions longues de `data/`.~~ Fait.
5. ~~Chantier 4 : backend / frontend.~~ Fait.
6. Chantier 5 : tests du frontend (en cours).
