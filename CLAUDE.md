# CLAUDE.md

Guidance for Claude Code in this repository.

## What this is

Murphy is a search engine over French legal documents (LEGIFRANCE / DILA data). The backend embeds a question, runs a hybrid search over the legal documents and their chunks, and serves a page of ranked documents with their matching passages; a document's full text is served on demand. The frontend is a search page with Dockview tabs (ADR-032). An LLM comes back in one place only (ADR-033): the user selects documents from the results, and the Explications tab summarizes and explains those documents and nothing else, streamed over SSE; it never qualifies a situation nor gives legal advice (its guardrails await their own ADR before production).

The backend is **stateless by design**: every request recomputes the whole pipeline, with no conversation history, no cache and no automatic retry (fail fast with a clear error). Think twice before adding caching, sessions or retries.

## Repository layout

One repository (ADR-016). The TypeScript projects are **npm workspaces** (`backend`, `frontend`, `packages/*`) with a single root `package-lock.json`: run `npm install` **at the root only** (its `postinstall` builds the contract).

- `backend/` — Express + TypeScript: the search API and the explanations stream.
- `frontend/` — Next.js 16 (App Router), React 19, Tailwind v4.
- `packages/contract/` — `@murphy/contract`: the zod schemas, and the types inferred from them, that backend and frontend exchange at runtime. One module per subpath (`search`, `explanations`, `errors`), no barrel; compiled by `tsc` to `dist/`. Only what crosses a runtime boundary between workspaces belongs in `packages/`.
- `data/` — Python/Kedro ingestion (XML → chunks → Mongo/OpenSearch/Neo4j), run offline. It shares the databases with the backend, never code.
- `docs/` — all the documentation:
  - `pilotage/`: `ADR/` (the ADRs, indexed in `INDEX.md`) and `WIP/` (work in progress);
  - `technical/`: `ARCHITECTURE.md` (the system view), then one folder per project, `backend/`, `data/` and `frontend/`, each with a `README.md` (index + operations) and an `ARCHITECTURE.md`; `data/reference/` holds the ingestion's reference docs.

## Commands

`npm run check` at the root runs what the CI runs for TypeScript: contract build, backend type-check + lint + tests, frontend type-check + lint + tests + format check + build. The CI's `python` job checks `data/` separately (see Ingestion). `next build` rewrites `frontend/next-env.d.ts`: restore it with `git checkout` afterwards.

Both ESLint configs enforce size limits: 300 lines per file (200 per frontend `.tsx`), 30 lines per function (blank lines and comments excluded), depth 3, 4 parameters, complexity 10, and `no-magic-numbers`. Tests are exempt from the function length and magic number rules. Shared HTTP statuses live in `backend/src/utils/httpStatus.ts`.

### Docker stack

The root scripts wrap Docker Compose and need `.env.dev` at the root (gitignored). It is the **only** env file of the system: Compose feeds it to the stack, and `data/` reads it by absolute path.

```bash
npm run up | watch | build | down | restart | logs | status | config
```

- No profiles: every script acts on the whole stack — `mongo`, `opensearch` (single node, written by `data/`, read by the backend: ADR-028), `opensearch-dashboards` (dev only), `neo4j`, `embedding-service` (TEI, needs an NVIDIA GPU), `backend` and `frontend`. `data/`'s `kedro run` needs the databases and TEI, so `npm run up` covers it too.
- `npm run up` recreates the containers whose configuration changed: run it after editing `.env.dev`, a plain `restart` keeps the old environment.
- Dev ports: frontend `3000`, backend `5000`, OpenSearch `9200` (security plugin disabled), OpenSearch Dashboards `5601`, Mongo `27017`, Neo4j `7474`/`7687`, TEI `5001`.
- Dev mounts only the sources (`backend/src`, `frontend/src`, `frontend/public`) with hot reload. Dependencies, app configs and the built contract live in the images: run `npm run build` then `npm run up` after changing `packages/contract`, a `package.json` or an app config.
- Production (`docker-compose.prod.yml`, no npm script) is not deployed yet: no reverse proxy, so the backend publishes `5000` and `CORS_ORIGIN` must be the frontend's public origin. `NEXT_PUBLIC_API_URL` is a build argument there (inlined by `next build`: changing it means rebuilding the image). Images run as `node`; `NODE_ENV` comes from the build target, never from `.env.dev`. TEI took 278 s to start with `microsoft/harrier-oss-v1-0.6b` (88 s of it downloading the weights on a fresh cache) and peaks at 4.1 GB of RAM while loading (1.1 GB after, 1.4 GB of VRAM): no `mem_limit` below that. OpenSearch keeps its security plugin there, but neither the backend nor `data/` authenticates yet.
- The build context is the repo root (`backend/Dockerfile`, `frontend/Dockerfile`); the root `.dockerignore` keeps `.env*`, `node_modules`, `data/` and `docs/` out.
- A CSS change that does not show in dev: Turbopack's cache is stale, even across restarts. `docker exec frontend rm -rf /app/frontend/.next/dev && docker restart frontend`.

### Backend (from `backend/`, or the root with `-w backend`)

Outside Docker no env file is loaded: export the variables first (`set -a; . ../.env.dev; set +a`, then override the Docker hostnames such as `OPENSEARCH_URL`).

```bash
npm run dev | dev:watch                  # ts-node / nodemon
npm run type-check | lint | build
npm test                                 # jest
npx jest path/to/file.test.ts            # one file; npx jest -t "name" for one test
```

Coverage thresholds (`jest.config.js`: lines/statements 65 %, functions 60 %, branches 40 %) are only checked by `npx jest --coverage`.

### Frontend (from `frontend/`)

`npm run dev` (Turbopack), `build`, `type-check`, `lint` (`--max-warnings=0`), `test` (Vitest + Testing Library, jsdom), `format` (Prettier; `format:check` runs in `check`). Path alias `@/*` → `src/*`.

Tests live in `src/__tests__/`, mirroring `src/`; `vitest.config.mts` runs them on Vite, outside Next. `src/__tests__/setup.ts` stubs what jsdom lacks (`<dialog>`, and for Dockview `ResizeObserver`, `matchMedia`, `scrollIntoView`).

## Serving: the search flow

The backend is a search API (ADR-030), with the same pipeline behind two routes:

- **`POST /api/v1/search`**, body `{ question, page?, pageSize? }` (`routes/search.ts` → `services/searchService.ts:searchDocuments`). The question travels in the body, never in a URL: no access log keeps it (ADR-010); the logs keep its length only.
- **`GET /api/v1/documents/:identifier`** (`routes/documents.ts` → `services/documentService.ts:readDocument`): `{ identifier, title, content, contentLength }` from Mongo, the full text served on demand; 404 `DOCUMENT_NOT_FOUND` for an unknown identifier.

The search pipeline:

1. **Paginate** — `pageSize` is one of `PAGINATION_SIZES` (default `10,25,50`; absent, the first; any other, a 400 `VALIDATION_ERROR`) and `page` defaults to 1 (`services/searchService.ts:toPageWindow`): `from = (page - 1) × pageSize`, `pageCount = ⌈PAGINATION_DEPTH / pageSize⌉` and the last page is truncated, `size = min(pageSize, PAGINATION_DEPTH − from)`, so `from + size` never exceeds the depth and no ranked document is lost (ADR-032 §8). A page beyond `pageCount` is refused (`PAGE_OUT_OF_RANGE`) before any call; a page within it but past the documents found is an empty list.
2. **Embed** → TEI.
3. **Search** → OpenSearch: a `hybrid` query of four sub-queries (lexical, references, passage k-NN, title k-NN; `infra/hybridQuery.ts`, identical to `docs/technical/data/reference/index-opensearch.md`), fused by the `murphy-rrf` search pipeline. It returns `size` ranked documents from `from`, each sub-query ranking `PAGINATION_DEPTH` (default 100, also the k-NN `k`; keep it constant across pages, or the ranking changes). A document's passages are its lexical and vector `inner_hits`, fused by RRF and deduplicated by `chunk_id` (`services/passageRanking.ts`); a document found without a matching passage has none (ADR-030 §3).
4. **Fetch documents** → Mongo `documents`, by `identifier`, for the title, the text and `metadata.statut` (the DILA `ETAT`, absent from decisions and sections). Each passage is cut out of the document's `content` between its `char_start`/`char_end` (code points, converted to UTF-16 in `services/passages.ts`). An invalid OpenSearch hit, a document missing from Mongo or out-of-range offsets raise a `CONTRACT_VIOLATION` `RagError` (ADR-015).
5. **Answer** `{ page, pageCount, pageSize, pageSizes, results }`: per document, in ranking order, `identifier`, `title`, `documentType`, `nature`, `isInForce` (`true` for `VIGUEUR` only, `false` for any other status, `VIGUEUR_DIFF` included, absent without one: ADR-032 §9) and its `passages` (`chunkId`, `text`, `start`, `end`: UTF-16 offsets into the `content` served by `GET /documents`). No score, no timing: the step durations are logged (`Search completed`).

Each result also carries `contentLength` (the ingestion's `content_length`, in code points; a document without it is a `CONTRACT_VIOLATION`: re-ingest), and the response carries `contextBudget` (`LLM_CONTEXT_MAX_CHARS`), the budget of the selection gauge.

The contract is `@murphy/contract/search` (the request, the search response, the document) and `@murphy/contract/errors` (the error codes).

## Serving: the explanations (ADR-033)

**`POST /api/v1/explanations`**, body `{ selection, messages }` (`@murphy/contract/explanations`): the identifiers in selection order, then the current segment of the conversation (the messages since the selection last changed); the server keeps nothing. `routes/explanations.ts` → `services/explanationService.ts`:

1. **Read** each document again from Mongo (`MongoDbClient.fetchExplainedDocuments`), never the client's text, in selection order; a missing one is 404 `DOCUMENT_NOT_FOUND`. Only the whitelisted metadata is projected.
2. **Context** (`services/explanationContext.ts`): each document behind its `[n]` marker, with its type, nature, parent text title, whitelisted metadata under French labels, and full text. The judges' and lawyers' names are never sent (loi n° 2019-222, art. 33). The system prompt is the versioned file `src/prompts/explanation.md`, copied to `dist/` by the build.
3. **Budget**: prompt + documents + segment, in code points, above `LLM_CONTEXT_MAX_CHARS` is 400 `CONTEXT_TOO_LARGE`. Consecutive user messages are merged.
4. **First fragment** (`openAnswer`): waited for at most `LLM_TIMEOUT` before the stream opens, so an LLM failure is still a real 502 `LLM_FAILED` / 504 `TIMEOUT`.
5. **Stream** (`services/explanationStream.ts`): the AI SDK's SSE protocol (`pipeUIMessageStreamToResponse`); a mid-stream error becomes an `error` event carrying the code alone.

A client leaving (`res.on('close')` without `res.writableEnded`) aborts the LLM call. Nothing of the content is logged: `Explanation completed` keeps counts, lengths, duration, outcome and tokens. `infra/llm.ts:LlmClient` is the only LLM seam (`@ai-sdk/openai-compatible`, `maxRetries: 0`, no provider named in the code); tests fake it, the CI never calls a real LLM. Two extra limiters (`middleware/explanationRateLimiter.ts`): 10 questions per minute per IP (`EXPLANATION_RATE_LIMIT_*`) and 200 calls per day for all clients (`EXPLANATION_DAILY_LIMIT`, in memory, refused requests not counted). The route has its own body limit, derived from the budget.

**Errors (ADR-030 §4)**: an HTTP status and a code (`status.message`), never the raw message, which stays in the logs; no stage leaves the backend. `errorHandler` maps a `RagError` through `utils/errorResponse.ts:toErrorResponse`: 400 `PAGE_OUT_OF_RANGE`/`CONTEXT_TOO_LARGE`, 404 `DOCUMENT_NOT_FOUND`, 502 `EMBEDDING_FAILED`/`SEARCH_FAILED`/`DB_FETCH_FAILED`/`LLM_FAILED`, 504 `TIMEOUT`, 500 `CONTRACT_VIOLATION`; anything else is 500 `INTERNAL`. A client leaving does not stop a search (ADR-030 §6); it does stop an explanation.

### Backend conventions

- **Config**: `src/config.ts` is the only reader of `process.env`. It validates the environment once at boot into a typed `readonly` `config` (an empty value counts as unset; a malformed integer stops the boot, as does a `PAGINATION_DEPTH` above 10 000, the k-NN `k` limit, or a `PAGINATION_SIZES` that is empty, repeats a size or holds one above the depth). `utils/configWarnings.ts:checkEnvironment` logs the defaulted variables and **stops the boot** when a required one is missing: `MONGODB_URI`, `OPENSEARCH_INDEX`, `EMBEDDING_QUERY_INSTRUCTION`, `LLM_BASE_URL` (an OpenAI-compatible base URL, without `/chat/completions`), `LLM_API_KEY`, `LLM_MODEL`. The LLM is not probed at boot. The full list is the `environment:` block of `docker-compose.base.yml` (note: Compose passes `EMBEDDING_MODEL` to the backend as `EMBEDDING_MODEL_NAME`).
- **Infra clients** (`src/infra/`): `EmbeddingClient`, `OpenSearchClient`, `MongoDbClient`, `LlmClient`; each takes its section of `config`. `initInfraClients(config)` builds them once at boot and may refuse the boot; requests use `getInfraClients()`. Never create a client per request. Failures go through `types/rag.ts:toRagError` → `RagError { stage, code }` (`TIMEOUT` when the error's type name ends in `TimeoutError`); the stage is for the logs only.
- **OpenSearch index**: `OPENSEARCH_INDEX`, the variable `data/` writes. At boot the backend refuses to start when OpenSearch is unreachable or the index does not exist, then writes the `murphy-rrf` search pipeline (idempotent `PUT`). The client has no retry and `OPENSEARCH_TIMEOUT` (10 s). No authentication yet. The embedding model must match the ingestion's (`microsoft/harrier-oss-v1-0.6b`, 1024 dimensions, cosine). `EmbeddingClient.embedQuestion` glues `EMBEDDING_QUERY_INSTRUCTION` (a critical variable, the model's instruction prefix) in front of the question, with no separator; the indexed passages and titles carry none, so changing it needs no re-ingestion (ADR-031).
- **HTTP**: base path `/api/v1`. JSON responses go through `utils/response.ts:buildApiResponse(code, message, data?)`. Async handlers are wrapped in `asyncHandler`; `errorHandler` keeps the 4xx of the JSON body parser's exposed errors (`INVALID_JSON` 400, `PAYLOAD_TOO_LARGE` 413, otherwise `INVALID_REQUEST_BODY`), gives a `RagError` the status of its code, and answers anything else with a 500 `INTERNAL`; a 4xx is logged as `warn`. Its codes are typed by the contract's `SearchErrorCode`. `notFoundHandler` and `errorHandler` come last in `app.ts`, after requestLogger → security (helmet, rate limit, CORS) → body parsing → routes.
- **Search requests**: validated by `validation/searchRequest.ts:parseSearchRequest` (the contract's schema, then `pageSize` against `PAGINATION_SIZES`; 400 `VALIDATION_ERROR` with `errors: [{ field, message }]`, whose zod messages never quote the question). Bodies are capped at 100 KiB (`utils/requestLimits.ts`). Two budgets per IP: the general limiter (600 per 15 min, `RATE_LIMIT_*`) covers every route; `POST /search` adds `middleware/searchRateLimiter.ts` (60/min, `SEARCH_RATE_LIMIT_*`). `trust proxy` is `false` in `app.ts` until a proxy is deployed.
- **Health**: `/api/v1/health` (alias `/api/v1/health/services`) probes TEI, OpenSearch (`/_cluster/health`), Mongo and the LLM (`GET {LLM_BASE_URL}/models`, authenticated): `ok`, `degraded` (1 down) or `down` (2+), 503 unless `ok`.
- **Logging**: Pino, one child logger per module (`rootLogger.child({ context: 'moduleName' })`).
- Neo4j is written by the ingestion but not yet read by the backend.

### Frontend conventions

One route, two states (ADR-032): `/` shows the home screen until a first search, then the workspace; the question never goes into the URL, and nothing survives a reload.

- **Layers**: components → stores (`stores/`, Zustand, no `persist`) → `lib/api` (`requestApi`: `fetch`, the `data` validated by the contract's schemas, failures turned into an `ApiError` code, `NETWORK` without a response). No component calls `fetch`. `searchStore` holds the question, page, page size, status, response and the last `contextBudget`; a new request aborts the previous one. `selectionStore` holds the selection, an ordered list that survives a new search. `explanationStore` holds the conversation: a module-level AI SDK `Chat` (so closing the tab keeps it), on the transport of `lib/api/explanations.ts` (`POST`, a refusal before the stream turned into an `ApiError`); `lib/api/explanationRequest.ts` builds the segment it sends. `errorStore` feeds the single error modal (`features/errors/`, one message per code, a `Record` the compiler keeps exhaustive).
- **Workspace**: `features/workspace/` is the only folder that imports Dockview. Dockview owns the layout; a document tab's params carry its own data (`{ identifier, passage? }`, no passage when opened from the selection or a citation). The selection sidebar (`features/selection/`) lives outside Dockview, right of the workspace; `Workspace.tsx` keeps the Dockview API from `onReady` and renders `SelectionSidebarAdapter`. `panelRegistry.tsx` maps each panel type to an adapter that takes Dockview's props and renders the feature panel with plain props and callbacks (`onOpenDocument`, `onError`): `results/`, `document/`, `explanation/` and `selection/` import neither Dockview nor `workspace/` nor each other (shared bits live in `components/ui/` or `lib/`, e.g. `InForceDot`, `lib/selectionBudget.ts`). The fixed panels (`results`, `explanation`) use their type as id; a document tab is `document:<identifier>`, so reopening it activates it.
- Colors are Tailwind classes from the `@theme` of `styles/globals.css` (`bg-secondary`, `text-tertiary`…): no theme context, no inline styles.
- `components/ui/Modal.tsx` is the generic modal (native `<dialog>`); `app/error.tsx` is the page's Error Boundary.
- Icons are decorative; an icon button carries its accessible name (`ButtonIcon`, `label`).

## Ingestion (`data/`, Python/Kedro)

Full documentation: `docs/technical/data/`. Key facts:

- The logic lives in the `ragcore` package (`data/src/ragcore/`, hexagonal); `data/src/data/` is a thin Kedro shell delegating to it.
- One pipeline (`__default__` = `ingestion`): nukeAll → ingest → resolveRelations → report. `ingest` streams (ADR-034 §2-§3): reading and parsing run in the node's thread and feed a queue bounded by the worker count, which the workers consume (saga Mongo → unformatted relations → transit relations → OpenSearch → Neo4j node); nothing materializes the corpus. A document is handled by one worker only because keys are unique per source. Relations wait between the phases in `MURPHY_DATA.transit_relations` (ADR-034 §4): cleared by `nukeAll` at every run start, consumed and deleted by phase 2; non-empty at its end fails the run (`TransitNotDrainedError`). Phase 2 finds the connected components of `contient` with a union-find over streamed pairs, then reduces each component alone (exactly the global reduction; a cycle keeps only its own component unreduced) and writes kept edges through a buffer, Neo4j `UNWIND` batches per verb; transit rows are deleted only after the buffer carrying their edges is flushed. Memory is bounded by the largest component, measured in `statistics.components`. The promotion of pending relations keeps `written_node_ids` in memory and queries Mongo by chunks of 10 000 (`$in` and the deletion's `$or`), under the 16 MB query limit.
- A file's key is its name without extension, which must be its `<ID>` (ADR-034 §1): connectors index the tree first (`discover()`, nothing parsed), then read a key's facets when emitting it (`fetch_all()`, a sync generator). A file whose `<ID>` differs from its name is rejected and counted (`document.id_mismatch`); test fixtures follow the same naming. The DILA export keeps stale copies of a file (often in the other `en_vigueur`/`non_vigueur` tree): per XML root, identical copies collapse to one and the most recent mtime wins (`sources/generic/copy_arbitration.py`: identical copies are a `duplicate_copy` collision, each older copy is counted `document.superseded` and detailed in `MURPHY_PROBLEMS.superseded`); copies with equal mtimes are all kept and the parser rejects the document (`facet_root_duplicated`). Extract the dumps with mtimes preserved (`tar`'s default), and keep a single dump per source root.
- One OpenSearch index, named by `OPENSEARCH_INDEX` (`OPENSEARCH_URL`, no auth yet) and rewritten in place, one `PUT` per document; its settings, analyzers and mapping are `ragcore/adapters/storage/opensearch/index_definition.json`, documented in `docs/technical/data/reference/index-opensearch.md` and `analyseurs.md` (keep the three identical). `ensure_index` never alters an existing index: re-ingest the whole corpus (`nuke_all` drops only that index) after changing the mapping, the analyzers, the chunking or the embedding model. The run status (`ok`/`degraded`/`failed`) comes from telemetry counters. Sizes and durations go to `MURPHY_META.statistics` (one document per run, written even on failure, ADR-034 §8), never into the run summary; the run summary's `counts` also count collisions and parse rejections per reason (`collision.<reason>`, `document.invalidated.<reason>`). The detail of the run's problems goes to the `MURPHY_PROBLEMS` database (ADR-036): one Mongo row per problem with its `run_id`, inserted in batches when the session closes, even on failure; rows accumulate across runs and `nuke_all` empties the database, which also holds `unformatted_relations`. The workers' aggregates reach the run in the `ingest` node, in a `finally`.
- Tuning: the chunking is in `.env.dev`, next to the embedding model it depends on (`CHUNKING_MAX_CHARS` 384, a legacy value sized for the previous model's window, and `CHUNKING_OVERLAP_CHARS` 25, both required). The embedding model is `EMBEDDING_MODEL` (`.env.dev`, shared with TEI and the backend); TEI is the only embedder, checked at startup (`GET /info`) and probed for the vector dimension. The mapping carries no dimension: `ensure_index` injects the measured one when it creates the index, and stops the run when an existing index has another one. `data/conf/base/parameters.yml` holds only dev conveniences, at its root: `nuke_all`, the embedding switch (ADR-012: off, passages are indexed without vectors), unconfigured-tag ingestion, source file paths in Mongo and Neo4j (`include_path`), the document text on Neo4j nodes (`include_content_neo4j`) (ADR-011) and `ingestion_ratio`, a `source → ratio` table, each in [0, 1] (ADR-034 §9: per source, the ⌈ratio × n⌉ keys of smallest blake2b hash, picked before any read; an absent source is 1, an unknown one stops the run, one at 0 is dropped from the run before discovery, and all at 0 stops it; the run summary's `sampling` carries each source's ratio with its retained/total counts). `ENVIRONMENT` is `dev` or `prod` (unset or empty = `prod`, any other value stops the run): only `dev` applies the file; in `prod` it is replaced by safe values, with a warning (ADR-019). `--params source=…` is set apart from the file and applies in both.
- Tooling: `kedro run` (`--params source=cass,jade` to restrict), `ruff`, `pytest` (`-m integration` uses testcontainers), `mypy` strict on `src/ragcore`.
- CI (`python` job, from `data/`): `uv sync --locked --extra dev`, then `uv run --locked` `ruff check .`, `ruff format --check .`, `mypy`, `pytest` (unit tests only: `addopts` excludes `integration`). Needs no `.env.dev` and no database.
