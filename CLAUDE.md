# CLAUDE.md

Guidance for Claude Code in this repository.

## What this is

Murphy is a RAG chatbot over French legal documents (LEGIFRANCE / DILA data). The backend embeds a question, searches legal-document chunks, reads the matching passages, and streams an LLM answer to the frontend along with its sources.

The backend is **stateless by design**: every request recomputes the whole pipeline, with no conversation history, no cache and no automatic retry (fail fast with a clear error). Think twice before adding caching, sessions or retries.

## Repository layout

One repository (ADR-016). The TypeScript projects are **npm workspaces** (`backend`, `frontend`, `packages/*`) with a single root `package-lock.json`: run `npm install` **at the root only** (its `postinstall` builds the contract).

- `backend/` — Express + TypeScript: the RAG serving pipeline.
- `frontend/` — Next.js 16 (App Router), React 19, Tailwind v4.
- `packages/contract/` — `@murphy/contract`: the zod schemas, and the types inferred from them, that backend and frontend exchange at runtime. One module per subpath (`@murphy/contract/messages`, `@murphy/contract/errors`), no barrel; compiled by `tsc` to `dist/`. Only what crosses a runtime boundary between workspaces belongs in `packages/`.
- `data/` — Python/Kedro ingestion (XML → chunks → Mongo/Qdrant/Neo4j), run offline. It shares the databases with the backend, never code.
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

- No profiles: every script acts on the whole stack — `mongo`, `qdrant`, `neo4j`, `embedding-service` (TEI, needs an NVIDIA GPU), `backend` and `frontend`. `data/`'s `kedro run` needs the databases and TEI, so `npm run up` covers it too.
- `npm run up` recreates the containers whose configuration changed: run it after editing `.env.dev`, a plain `restart` keeps the old environment.
- Dev ports: frontend `3000`, backend `5000`, Qdrant `6333`, Mongo `27017`, Neo4j `7474`/`7687`, TEI `5001`.
- Dev mounts only the sources (`backend/src`, `frontend/src`, `frontend/public`) with hot reload. Dependencies, app configs and the built contract live in the images: run `npm run build` then `npm run up` after changing `packages/contract`, a `package.json` or an app config.
- Production (`docker-compose.prod.yml`, no npm script) is not deployed yet: no reverse proxy, so the backend publishes `5000` and `CORS_ORIGIN` must be the frontend's public origin. `NEXT_PUBLIC_API_URL` is a build argument there (inlined by `next build`: changing it means rebuilding the image). Images run as `node`; `NODE_ENV` comes from the build target, never from `.env.dev`. TEI takes ~4 min and over 4 GB of RAM to start: no `mem_limit` below that.
- The build context is the repo root (`backend/Dockerfile`, `frontend/Dockerfile`); the root `.dockerignore` keeps `.env*`, `node_modules`, `data/` and `docs/` out.
- A CSS change that does not show in dev: Turbopack's cache is stale, even across restarts. `docker exec frontend rm -rf /app/frontend/.next/dev && docker restart frontend`.

### Backend (from `backend/`, or the root with `-w backend`)

Outside Docker no env file is loaded: export the variables first (`set -a; . ../.env.dev; set +a`, then override the Docker hostnames such as `QDRANT_URL`).

```bash
npm run dev | dev:watch                  # ts-node / nodemon
npm run type-check | lint | build
npm test                                 # jest
npx jest path/to/file.test.ts            # one file; npx jest -t "name" for one test
```

Coverage thresholds (`jest.config.js`: lines/statements 65 %, functions 60 %, branches 40 %) are only checked by `npx jest --coverage`.

### Frontend (from `frontend/`)

`npm run dev` (Turbopack), `build`, `type-check`, `lint` (`--max-warnings=0`), `test` (Vitest + Testing Library, jsdom), `format` (Prettier; `format:check` runs in `check`). Path alias `@/*` → `src/*`.

Tests live in `src/__tests__/`, mirroring `src/`; `vitest.config.mts` runs them on Vite, outside Next. `src/__tests__/fakeWebSocket.ts` plays the backend's side of the chat socket (`stubWebSocket()`).

## Serving: the RAG request flow

The pipeline is `backend/src/services/chatService.ts:createChatStream(messages, abortSignal)`:

1. **Extract the question** — the text parts of the last `user` message (requests carry an AI SDK `messages` array; the frontend sends only that last question).
2. **Embed** → TEI.
3. **Retrieve** → Qdrant top-K (`RETRIEVAL_TOP_K`, default 5).
4. **Fetch passages** → Mongo `documents`, by `identifier`. Each passage is cut out of its parent's `content` between the payload's `char_start`/`char_end` (code points, converted to UTF-16 in `services/passages.ts`). A missing parent or out-of-range offsets raise a `CONTRACT_VIOLATION` `RagError` (ADR-015).
5. **Stream the sources**, before the LLM, in ranking order: a `data-parentDocument` part once per document, then a `data-document` part per passage (`highlightStart`/`highlightEnd`, UTF-16).
6. **Stream the LLM** — only the passage texts go into the system prompt (`config.llm.systemPrompt`, overridable by `SYSTEM_PROMPT`); tokens become `text-delta` parts.
7. **Finish** — a `finish` part with the `ragTiming` metadata.

The stream contract is `AppUIMessage` (`@murphy/contract/messages`): the backend compiles against it, the frontend validates incoming parts with the same zod schemas: the `data-*` parts in `lib/webSocketChatTransport.ts` (ai 6.0.x never applies `useChat`'s `dataPartSchemas`: it looks them up by part type, `data-document`, not by name), the metadata in `useChat({ messageMetadataSchema })`. A change breaks both compilations at once.

One stream, three transports — change `createChatStream` once:
- **WebSocket** `/api/v1/chat/ws` (`routes/chatWebSocket.ts`), the one the frontend uses (`hooks/useRagChat.ts` plugs `lib/webSocketChatTransport.ts` into `useChat`);
- **POST** `/api/v1/chat/streams` (SSE) and `/api/v1/chat/completions` (JSON) — `routes/chat.ts`.

**Errors and abort (ADR-017)**: an `error` part's `errorText` is a serialized `ChatError` `{ stage, code }` (`@murphy/contract/errors`, built by `types/rag.ts:toChatError`), never the raw message, which stays in the logs. The frontend names the failed stage in a modal. Closing the socket or the HTTP response raises the `AbortSignal`: the pipeline stops before the LLM, or cuts the LLM request.

### Backend conventions

- **Config**: `src/config.ts` is the only reader of `process.env`. It validates the environment once at boot into a typed `readonly` `config` (an empty value counts as unset; a malformed number stops the boot). `utils/configWarnings.ts` logs the missing and defaulted variables. The full list is the `environment:` block of `docker-compose.base.yml` (note: Compose passes `EMBEDDING_MODEL` to the backend as `EMBEDDING_MODEL_NAME`).
- **Infra clients** (`src/infra/`): `EmbeddingClient`, `QdrantVectorClient`, `LLMProvider` (OpenAI-compatible API), `MongoDbClient`; each takes its section of `config`. `initInfraClients(config)` builds them once at boot and may refuse the boot; requests use `getInfraClients()`. Never create a client per request. Failures go through `types/rag.ts:toRagError` → `RagError { stage, code }` (`TIMEOUT` when the error's type name ends in `TimeoutError`).
- **Qdrant collection**: a fixed name, `QDRANT_COLLECTION`, read by both the backend and the ingestion from `.env.dev` (ADR-018). The backend refuses to boot when the collection does not exist. The embedding model must match the ingestion's (`all-mpnet-base-v2`, 768 dimensions, cosine).
- **HTTP**: base path `/api/v1`. JSON responses go through `utils/response.ts:buildApiResponse(code, message, data?)`. Async handlers are wrapped in `asyncHandler`; `errorHandler` keeps the 4xx of the JSON body parser's exposed errors (`INVALID_JSON` 400, `PAYLOAD_TOO_LARGE` 413, logged as `warn`) and answers anything else with a 500. `notFoundHandler` and `errorHandler` come last in `app.ts`, after requestLogger → security (helmet, rate limit, CORS) → body parsing → routes.
- **Chat requests**: validated by `validation/chatRequest.ts:parseChatRequest` (HTTP and WebSocket). Bodies and WebSocket messages share one size limit (`utils/requestLimits.ts`, 100 KiB); the socket also checks `Origin` against `CORS_ORIGIN` and closes after 10 s without a message. Every WebSocket keeps an `error` listener: `ws` throws an unheard one (invalid frame, oversized message) as an uncaught exception, which stops the server. One stream budget per IP (10/min by default, `middleware/streamRateLimiter.ts`), shared by `/streams`, `/completions` and WebSocket messages. `trust proxy` is `false` in `app.ts` until a proxy is deployed.
- **Health**: `/api/v1/health` (alias `/api/v1/health/services`) probes TEI, Qdrant and Mongo: `ok`, `degraded` (1 down) or `down` (2+), 503 unless `ok`.
- **Logging**: Pino, one child logger per module (`rootLogger.child({ context: 'moduleName' })`).
- Neo4j is written by the ingestion but not yet read by the backend.

### Frontend conventions

- Colors are Tailwind classes from the `@theme` of `styles/globals.css` (`bg-secondary`, `text-tertiary`…): no theme context, no inline styles.
- `components/ui/Modal.tsx` is the generic modal (native `<dialog>`); `app/error.tsx` is the page's Error Boundary.
- Icons are decorative; an icon button carries its accessible name (`ButtonIcon`, `label`).

## Ingestion (`data/`, Python/Kedro)

Full documentation: `docs/technical/data/`. Key facts:

- The logic lives in the `ragcore` package (`data/src/ragcore/`, hexagonal); `data/src/data/` is a thin Kedro shell delegating to it.
- One pipeline (`__default__` = `ingestion`): nukeAll → connect → parseDocuments → ingest (saga Mongo → unformatted relations → Qdrant → Neo4j node) → resolveRelations → report.
- One Qdrant collection, named by `QDRANT_COLLECTION` and rewritten in place: re-ingest the whole corpus after changing the chunking or the embedding model. The run status (`ok`/`degraded`/`failed`) comes from telemetry counters.
- Tuning: the chunking is in `.env.dev`, next to the embedding model it depends on (`CHUNKING_MAX_CHARS` 384, `CHUNKING_OVERLAP_CHARS` 25, both required). The embedding model is `EMBEDDING_MODEL` (`.env.dev`, shared with TEI and the backend); TEI is the only embedder, checked at startup (`GET /info`) and probed for the vector dimension. `data/conf/base/parameters.yml` holds only dev conveniences, at its root: `nuke_all`, the embedding switch (ADR-012), unconfigured-tag ingestion, source file paths in Mongo and Neo4j (`include_path`) and the document text on Neo4j nodes (`include_content_neo4j`) (ADR-011). `ENVIRONMENT` is `dev` or `prod` (unset or empty = `prod`, any other value stops the run): only `dev` applies the file; in `prod` it is replaced by safe values, with a warning (ADR-019). `--params source=…` is set apart from the file and applies in both.
- Tooling: `kedro run` (`--params source=cass,jade` to restrict), `ruff`, `pytest` (`-m integration` uses testcontainers), `mypy` strict on `src/ragcore`.
- CI (`python` job, from `data/`): `uv sync --locked --extra dev`, then `uv run --locked` `ruff check .`, `ruff format --check .`, `mypy`, `pytest` (unit tests only: `addopts` excludes `integration`). Needs no `.env.dev` and no database.
