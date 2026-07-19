# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Murphy is a RAG (Retrieval-Augmented Generation) chatbot for French legal documents (LEGIFRANCE data). A user asks a question; the backend embeds it, does semantic search over legal-document chunks, fetches the matching content, and streams an LLM answer back to the frontend along with the source documents that informed it.

The serving system (backend) is **stateless by design**: every request recomputes the full pipeline, there is no conversational history stored, and there are no automatic retries (fail-fast with a clear error). Keep this in mind before adding caching, sessions, or retry layers.

## Repository layout

This is the **parent repo** (orchestration + infra). The three application projects are
**git submodules**, each its own GitHub repo. Clone with `git clone --recursive`, or run
`git submodule update --init --recursive` after a plain clone. To edit application code,
commit and push **inside** the submodule, then commit the updated pointer here.

- `backend/` — **submodule** ([murphy-backend](https://github.com/left-eyebr0w/murphy-backend)). Express + TypeScript API (the RAG **serving** orchestrator). The bulk of the runtime request logic.
- `frontend/` — **submodule** ([murphy-frontend](https://github.com/left-eyebr0w/murphy-frontend)). Next.js 16 (App Router) + React 19 + Tailwind v4 chat UI.
- `data/` — **submodule** ([murphy-data](https://github.com/left-eyebr0w/murphy-data)). Python/Kedro **ingestion** project that populates the databases (XML → parse → chunk → embed → Mongo/Qdrant/Neo4j). Runs offline, separately from the serving stack.
- `docker-compose.base.yml` + `.dev.yml` / `.prod.yml` — the stack at the repo root: backend, frontend, MongoDB, Qdrant, Neo4j, and a HuggingFace TEI embedding service (GPU). Build contexts are `./backend` and `./frontend`. Two Compose **profiles** share the same DB/embedding services: `ingest` (just the databases + TEI, for running `data/`'s `kedro run` against them) and `serve` (adds backend + frontend). The `data/` pipeline code itself still runs outside Docker, invoked manually.
- `docs/` — **cross-cutting docs only**: `pilotage/` (PM² steering), `product/` (vision, versions, ADRs), and `technical/ARCHITECTURE.md` (the system-level view). **Detailed technical documentation lives in each submodule's `docs/` folder** (`backend/docs/`, `frontend/docs/`, `data/docs/` — each with `README.md` index+operations, `ARCHITECTURE.md`, and `reference/`).

Ingestion and serving share databases but no code. The backend assumes the databases are already populated by the `data/` pipeline.

## Serving stack (Docker)

The root `package.json` scripts wrap Docker Compose (all require an `.env.dev` file at the repo root, which is gitignored — create it before running):

```bash
npm run serve:up     # build+start backend+frontend+DBs+TEI, detached
npm run serve:watch  # same, foreground (streams logs)
npm run serve:build  # docker compose build
npm run serve:down   # stop the serve profile only
npm run up            # alias for serve:up
npm run watch          # alias for serve:watch
npm run build          # alias for serve:build

npm run ingest:up     # start just DBs+TEI (detached), for running data/'s kedro pipeline against them
npm run ingest:watch  # same, foreground
npm run ingest:down   # stop the ingest profile only
npm run ingest:logs / ingest:status

npm run down     # stops BOTH profiles — needed because `docker compose down` without --profile silently leaves profiled services running (reports success either way)
npm run restart  # restarts both profiles
npm run logs     # tails both profiles
npm run status   # container status table, both profiles
```

`qdrant`/`mongo` have no profile (always up under either); `backend`/`frontend` are `serve`-only; `embedding-service` is in both profiles (needed by the ingestion pipeline for embedding *and* by the backend at request time). Because of the silent-leak behavior of unprofiled `down`, always use the npm scripts above rather than raw `docker compose down`.

Dev ports: frontend `3000`, backend `5000`, Qdrant `6333`, Mongo `27017`, Neo4j `7474`/`7687`, embedding service `5001→80`. Dev mode mounts source into the containers with hot-reload (`ts-node` watch for backend, `next dev` for frontend).

The embedding service requires an **NVIDIA GPU** (declared in `docker-compose.dev.yml`). Without one, run backend/frontend locally instead and point env vars at reachable services.

### Backend without Docker

From `backend/`:

```bash
npm run dev          # ts-node src/server.ts
npm run dev:watch    # nodemon + ts-node (auto-restart)
npm run build        # tsc -> dist/
npm run type-check   # tsc --noEmit
npm run lint         # eslint src
npm test             # jest
npm run test:watch
npx jest path/to/file.test.ts          # run one test file
npx jest -t "name of test"             # run tests matching a name
```

Jest enforces coverage thresholds (`jest.config.js`: lines/statements 65%, functions 60%, branches 40%). `src/server.ts` is excluded from coverage.

### Frontend without Docker

From `frontend/`: `npm run dev` (Turbopack), `npm run build`, `npm run lint`. TS path alias `@/*` → `frontend/src/*`.

## Architecture: the RAG request flow (serving)

The core pipeline lives in `backend/src/services/chatService.ts:createChatStream`. Trace it through:

1. **Extract question** — the last `user` message's text parts (`extractQuestionFromMessages`). Requests carry an AI SDK `messages` array, not a bare `question` string.
2. **Embed** (`ragService.embedQuestion`) → TEI embedding service.
3. **Retrieve** (`ragService.retrieveChunks`) → Qdrant top-K (`RETRIEVAL_TOP_K`, default 5).
4. **Stream sources first** — each Qdrant hit is written to the stream as a `data-document` part *before the LLM runs*, so the UI shows sources immediately.
5. **Fetch content** (`ragService.fetchChunkDocuments`) → MongoDB, by `chunkId`. This content is used only to build the LLM context, never sent directly to the client.
6. **Stream LLM** — context is injected into the system prompt (`getDefaultSystemPrompt`, French legal-assistant prompt, overridable via `SYSTEM_PROMPT` env), then `llmProvider.stream()` tokens are written as `text-delta` parts.
7. **Finish** — a `finish` part carries `ragTiming` metadata (per-stage latency in ms).

The stream is built with the Vercel **AI SDK** (`createUIMessageStream` / `pipeUIMessageStreamToResponse`). The message/part contract is `AppUIMessage` in `backend/src/types/messages.ts` — keep backend and frontend (`frontend/src/types/messages.ts`) in sync; the custom data part is `{ document: DocumentChunk }` and metadata is `{ ragTiming }`.

### Two transports, same pipeline

`createChatStream` produces one stream consumed three ways:
- **WebSocket** (`routes/chatWebSocket.ts`, path `/api/v1/chat/ws`) — this is what the frontend actually uses (`useRagChat.ts` implements a custom `WebSocketChatTransport` over `@ai-sdk/react`'s `useChat`). One message in, stream of JSON parts out, socket closes.
- **POST `/api/v1/chat/streams`** (SSE) and **POST `/api/v1/chat/completions`** (drains the stream to a single JSON response) — `routes/chat.ts`. Useful for testing/non-streaming clients.

When changing the pipeline, change `createChatStream` once — all three paths inherit it.

### Infrastructure clients (`backend/src/infra/`)

`EmbeddingClient` (TEI), `QdrantVectorClient`, `LLMProvider` (Mammouth.AI-style OpenAI-compatible API), and the MongoDB client. The barrel `infra/index.ts` exposes them as **lazy singletons via `Proxy`** (`embeddingClient`, `qdrantClient`, `llmProvider`) — instantiated on first property access, reused across requests. Import these singletons rather than `new`-ing clients per request. Mongo is the exception: it has an explicit `initMongoClient()` (called at boot in `server.ts`) and `closeMongoClient()` for graceful shutdown.

### Cross-cutting backend conventions

- **API responses** go through `utils/response.ts:buildApiResponse(code, message, data?)` → `{ status: {code, message}, data?, meta: {timestamp, traceId} }`. Use it for all JSON responses for consistency.
- **Logging** is Pino (`utils/logger.ts`). Create a child logger per module: `rootLogger.child({ context: 'moduleName' })`. Logs are structured JSON.
- **Errors**: wrap async route handlers in `middleware/errorHandler.ts:asyncHandler`; `errorHandler` + `notFoundHandler` are registered last in `app.ts`.
- **Middleware order** (`app.ts`): requestLogger → helmet/rate-limit/CORS (`middleware/security.ts`) → body parsing → routes → error handlers. The chat stream route additionally uses `streamRateLimiter` and `express-validator` (`middleware/validation.ts`).
- **API base path** is `/api/v1`. Health is `/api/v1/health` (+ `/services` for per-service latency); it reports `ok`/`degraded` (1 service down)/`down` (2+ down) and returns 503 when not ok.

## Ingestion pipeline (`data/`, Python/Kedro)

A Kedro project that ingests the DILA XML corpora (LEGI + the 5 case-law bases: CAPP, CASS, INCA, JADE, CONSTIT) and writes documents/vectors/graph into the same MongoDB / Qdrant / Neo4j the backend reads from. It runs **offline and out-of-band** — not part of the Docker serving stack, and the backend never calls into it.

**Full documentation: `data/docs/`** (architecture, node-by-node pipeline reference, data model, configuration, telemetry). Key structural facts:

- All pipeline logic lives in the **`ragcore` package, vendored at `data/src/ragcore/`** (hexagonal: `core/` domain + ports, `adapters/`, `application/`, `sources/`, `orchestration/kedro/`). `data/src/data/` is a thin Kedro shell that delegates to it (`src/data/datasets|models|utils` are unused vestiges).
- One pipeline (`__default__` = `ingestion`): cleanup → nukeAll → connect → computeIdempotence → ingest (4-worker pool, saga Mongo→Qdrant→Neo4j-node) → resolveRelations (graph edges, pending-relations cache) → report. Runtime objects are `MemoryDataset`s injected by `TelemetryHooks.before_pipeline_run`.
- **Qdrant collection names are derived** (blake2b fingerprint of the workflow config: normalization + chunking + embedding), never hand-written. A run that ends `ok` publishes the pointer `MURPHY_META.meta_published_collection`, which the backend reads at boot (`backend/src/infra/collectionPointer.ts`).
- `data/conf/base/parameters.yml` is the tuning surface (`chunk_size: 384` chars / `chunk_overlap: 25`, normalization `v1`, `all-mpnet-base-v2` 768-dim). Env config is the **root `.env.dev` only** (read by absolute path — there is no `.env` in `data/`). `ENVIRONMENT=dev` gates `nuke_all`, the embedding switch (ADR-023) and Neo4j node hydration (ADR-022); the default is `prod` = locked.
- Run status (`ok`/`degraded`/`failed`) is derived from telemetry counters (completeness equation), not from exceptions. Only `ok` runs publish.

Tooling: `kedro run` (`--params source=cass,jade` to restrict), `kedro viz`, `ruff`, `pytest` (unit+golden need no DBs; `-m integration` uses testcontainers), `mypy` strict on `src/ragcore`.

## Configuration

Backend runtime config is environment-driven (see the `environment:` block in `docker-compose.base.yml` for the full list). Key vars: `MONGODB_URI/DATABASE/COLLECTION`, `QDRANT_URL/COLLECTION`, `EMBEDDING_SERVICE_URL/EMBEDDING_MODEL`, `LLM_API_ENDPOINT/API_KEY/MODEL/TEMPERATURE/MAX_TOKENS`, `RETRIEVAL_TOP_K`, `RETRIEVAL_MIN_SCORE`, `SYSTEM_PROMPT`, plus rate-limit and CORS settings. `backend/src/utils/configWarnings.ts:checkEnvironment()` runs at startup and warns about missing/suspect config — check it for the authoritative expected-var list.

There is **one** env file for the whole system: `.env.dev` at the repo root (gitignored). Docker Compose feeds it to the serving stack, and the ingestion project reads the same file by absolute path (`ragcore/adapters/config/settings.py`) — a `.env` inside `data/` has no effect. One file so the TEI container and the pipeline can never disagree on the embedding model.

The embedding model and dimensions must match between ingestion and serving: the pipeline embeds with `all-mpnet-base-v2` (768-dim, Cosine), so the TEI service and `RETRIEVAL_*` settings on the backend must align with vectors of the same model/dimensionality. `QDRANT_COLLECTION` is only a **fallback**: the backend resolves the collection from the pointer published by the last `ok` ingestion run (`MURPHY_META.meta_published_collection`) and refuses to boot if the resolved collection doesn't exist.

Neo4j is provisioned in compose and written by the ingestion pipeline, but is not yet wired into the backend request path — it's reserved for future graph-based context enrichment.
