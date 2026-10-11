# CLAUDE.md

Guidance for Claude Code in this repository.

## What this is

Murphy is a search engine over French legal documents (LEGIFRANCE / DILA data). The backend embeds a question, runs a hybrid search over the legal documents and their chunks, and serves a page of ranked documents with their matching passages; a document's full text is served on demand. The LLM and the chat stream are gone (ADR-030); the frontend still speaks that stream and is out of service until ADR-032 adapts it.

The backend is **stateless by design**: every request recomputes the whole pipeline, with no conversation history, no cache and no automatic retry (fail fast with a clear error). Think twice before adding caching, sessions or retries.

## Repository layout

One repository (ADR-016). The TypeScript projects are **npm workspaces** (`backend`, `frontend`, `packages/*`) with a single root `package-lock.json`: run `npm install` **at the root only** (its `postinstall` builds the contract).

- `backend/` — Express + TypeScript: the search API.
- `frontend/` — Next.js 16 (App Router), React 19, Tailwind v4.
- `packages/contract/` — `@murphy/contract`: the zod schemas, and the types inferred from them, that backend and frontend exchange at runtime. One module per subpath (`@murphy/contract/search`; `messages` and `errors`, frozen until ADR-032), no barrel; compiled by `tsc` to `dist/`. Only what crosses a runtime boundary between workspaces belongs in `packages/`.
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

Tests live in `src/__tests__/`, mirroring `src/`; `vitest.config.mts` runs them on Vite, outside Next. `src/__tests__/fakeWebSocket.ts` plays the backend's side of the chat socket (`stubWebSocket()`), which the backend no longer serves: the frontend is frozen until ADR-032 (ADR-030 §8).

## Serving: the search flow

The backend is a search API (ADR-030), with the same pipeline behind two routes:

- **`POST /api/v1/search`**, body `{ question, page? }` (`routes/search.ts` → `services/searchService.ts:searchDocuments`). The question travels in the body, never in a URL: no access log keeps it (ADR-010); the logs keep its length only.
- **`GET /api/v1/documents/:identifier`** (`routes/documents.ts` → `services/documentService.ts:readDocument`): `{ identifier, title, content }` from Mongo, the full text served on demand; 404 `DOCUMENT_NOT_FOUND` for an unknown identifier.

The search pipeline:

1. **Paginate** — `page` (default 1) gives `from = (page - 1) × PAGINATION_SIZE`; `pageCount = ⌊PAGINATION_DEPTH / PAGINATION_SIZE⌋` (10 by default), so `from + size` never exceeds the depth. A page beyond it is refused (`PAGE_OUT_OF_RANGE`) before any call; a page within it but past the documents found is an empty list.
2. **Embed** → TEI.
3. **Search** → OpenSearch: a `hybrid` query of four sub-queries (lexical, references, passage k-NN, title k-NN; `infra/hybridQuery.ts`, identical to `docs/technical/data/reference/index-opensearch.md`), fused by the `murphy-rrf` search pipeline. It returns `PAGINATION_SIZE` ranked documents from `from`, each sub-query ranking `PAGINATION_DEPTH` (default 100, also the k-NN `k`; keep it constant across pages, or the ranking changes). A document's passages are its lexical and vector `inner_hits`, fused by RRF and deduplicated by `chunk_id` (`services/passageRanking.ts`); a document found without a matching passage has none (ADR-030 §3).
4. **Fetch documents** → Mongo `documents`, by `identifier`, for the title and the text. Each passage is cut out of the document's `content` between its `char_start`/`char_end` (code points, converted to UTF-16 in `services/passages.ts`). An invalid OpenSearch hit, a document missing from Mongo or out-of-range offsets raise a `CONTRACT_VIOLATION` `RagError` (ADR-015).
5. **Answer** `{ page, pageCount, results }`: per document, in ranking order, `identifier`, `title`, `documentType`, `nature` and its `passages` (`chunkId`, `text`, `start`, `end`: UTF-16 offsets into the `content` served by `GET /documents`). No score, no timing: the step durations are logged (`Search completed`).

The contract is `@murphy/contract/search`: the zod schemas of the request, the search response, the document and the error codes. `@murphy/contract/messages` and `errors` describe the old chat stream; the backend no longer imports them, and they stay frozen for the frontend until ADR-032.

**Errors (ADR-030 §4)**: an HTTP status and a code (`status.message`), never the raw message, which stays in the logs; no stage leaves the backend. `errorHandler` maps a `RagError` through `utils/errorResponse.ts:toErrorResponse`: 400 `PAGE_OUT_OF_RANGE`, 404 `DOCUMENT_NOT_FOUND`, 502 `EMBEDDING_FAILED`/`SEARCH_FAILED`/`DB_FETCH_FAILED`, 504 `TIMEOUT`, 500 `CONTRACT_VIOLATION`; anything else is 500 `INTERNAL`. A client leaving does not stop the pipeline (ADR-030 §6).

### Backend conventions

- **Config**: `src/config.ts` is the only reader of `process.env`. It validates the environment once at boot into a typed `readonly` `config` (an empty value counts as unset; a malformed integer stops the boot, as does a `PAGINATION_DEPTH` below `PAGINATION_SIZE` or above 10 000, the k-NN `k` limit). `utils/configWarnings.ts` logs the missing and defaulted variables. The full list is the `environment:` block of `docker-compose.base.yml` (note: Compose passes `EMBEDDING_MODEL` to the backend as `EMBEDDING_MODEL_NAME`).
- **Infra clients** (`src/infra/`): `EmbeddingClient`, `OpenSearchClient`, `MongoDbClient`; each takes its section of `config`. `initInfraClients(config)` builds them once at boot and may refuse the boot; requests use `getInfraClients()`. Never create a client per request. Failures go through `types/rag.ts:toRagError` → `RagError { stage, code }` (`TIMEOUT` when the error's type name ends in `TimeoutError`); the stage is for the logs only.
- **OpenSearch index**: `OPENSEARCH_INDEX`, the variable `data/` writes. At boot the backend refuses to start when OpenSearch is unreachable or the index does not exist, then writes the `murphy-rrf` search pipeline (idempotent `PUT`). The client has no retry and `OPENSEARCH_TIMEOUT` (10 s). No authentication yet. The embedding model must match the ingestion's (`microsoft/harrier-oss-v1-0.6b`, 1024 dimensions, cosine). `EmbeddingClient.embedQuestion` glues `EMBEDDING_QUERY_INSTRUCTION` (a critical variable, the model's instruction prefix) in front of the question, with no separator; the indexed passages and titles carry none, so changing it needs no re-ingestion (ADR-031).
- **HTTP**: base path `/api/v1`. JSON responses go through `utils/response.ts:buildApiResponse(code, message, data?)`. Async handlers are wrapped in `asyncHandler`; `errorHandler` keeps the 4xx of the JSON body parser's exposed errors (`INVALID_JSON` 400, `PAYLOAD_TOO_LARGE` 413, otherwise `INVALID_REQUEST_BODY`), gives a `RagError` the status of its code, and answers anything else with a 500 `INTERNAL`; a 4xx is logged as `warn`. Its codes are typed by the contract's `SearchErrorCode`. `notFoundHandler` and `errorHandler` come last in `app.ts`, after requestLogger → security (helmet, rate limit, CORS) → body parsing → routes.
- **Search requests**: validated by `validation/searchRequest.ts:parseSearchRequest` (the contract's schema; 400 `VALIDATION_ERROR` with `errors: [{ field, message }]`, whose zod messages never quote the question). Bodies are capped at 100 KiB (`utils/requestLimits.ts`). Two budgets per IP: the general limiter (600 per 15 min, `RATE_LIMIT_*`) covers every route; `POST /search` adds `middleware/searchRateLimiter.ts` (60/min, `SEARCH_RATE_LIMIT_*`). `trust proxy` is `false` in `app.ts` until a proxy is deployed.
- **Health**: `/api/v1/health` (alias `/api/v1/health/services`) probes TEI, OpenSearch (`/_cluster/health`) and Mongo: `ok`, `degraded` (1 down) or `down` (2+), 503 unless `ok`.
- **Logging**: Pino, one child logger per module (`rootLogger.child({ context: 'moduleName' })`).
- Neo4j is written by the ingestion but not yet read by the backend.

### Frontend conventions

- Colors are Tailwind classes from the `@theme` of `styles/globals.css` (`bg-secondary`, `text-tertiary`…): no theme context, no inline styles.
- `components/ui/Modal.tsx` is the generic modal (native `<dialog>`); `app/error.tsx` is the page's Error Boundary.
- Icons are decorative; an icon button carries its accessible name (`ButtonIcon`, `label`).

## Ingestion (`data/`, Python/Kedro)

Full documentation: `docs/technical/data/`. Key facts:

- The logic lives in the `ragcore` package (`data/src/ragcore/`, hexagonal); `data/src/data/` is a thin Kedro shell delegating to it.
- One pipeline (`__default__` = `ingestion`): nukeAll → connect → parseDocuments → ingest (saga Mongo → unformatted relations → OpenSearch → Neo4j node) → resolveRelations → report.
- One OpenSearch index, named by `OPENSEARCH_INDEX` (`OPENSEARCH_URL`, no auth yet) and rewritten in place, one `PUT` per document; its settings, analyzers and mapping are `ragcore/adapters/storage/opensearch/index_definition.json`, documented in `docs/technical/data/reference/index-opensearch.md` and `analyseurs.md` (keep the three identical). `ensure_index` never alters an existing index: re-ingest the whole corpus (`nuke_all` drops only that index) after changing the mapping, the analyzers, the chunking or the embedding model. The run status (`ok`/`degraded`/`failed`) comes from telemetry counters.
- Tuning: the chunking is in `.env.dev`, next to the embedding model it depends on (`CHUNKING_MAX_CHARS` 384, a legacy value sized for the previous model's window, and `CHUNKING_OVERLAP_CHARS` 25, both required). The embedding model is `EMBEDDING_MODEL` (`.env.dev`, shared with TEI and the backend); TEI is the only embedder, checked at startup (`GET /info`) and probed for the vector dimension. The mapping carries no dimension: `ensure_index` injects the measured one when it creates the index, and stops the run when an existing index has another one. `data/conf/base/parameters.yml` holds only dev conveniences, at its root: `nuke_all`, the embedding switch (ADR-012: off, passages are indexed without vectors), unconfigured-tag ingestion, source file paths in Mongo and Neo4j (`include_path`) and the document text on Neo4j nodes (`include_content_neo4j`) (ADR-011). `ENVIRONMENT` is `dev` or `prod` (unset or empty = `prod`, any other value stops the run): only `dev` applies the file; in `prod` it is replaced by safe values, with a warning (ADR-019). `--params source=…` is set apart from the file and applies in both.
- Tooling: `kedro run` (`--params source=cass,jade` to restrict), `ruff`, `pytest` (`-m integration` uses testcontainers), `mypy` strict on `src/ragcore`.
- CI (`python` job, from `data/`): `uv sync --locked --extra dev`, then `uv run --locked` `ruff check .`, `ruff format --check .`, `mypy`, `pytest` (unit tests only: `addopts` excludes `integration`). Needs no `.env.dev` and no database.
