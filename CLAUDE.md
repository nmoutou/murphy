# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Murphy is a RAG (Retrieval-Augmented Generation) chatbot for French legal documents (LEGIFRANCE data). A user asks a question; the backend embeds it, does semantic search over legal-document chunks, fetches the matching content, and streams an LLM answer back to the frontend along with the source documents that informed it.

The serving system (backend) is **stateless by design**: every request recomputes the full pipeline, there is no conversational history stored, and there are no automatic retries (fail-fast with a clear error). Keep this in mind before adding caching, sessions, or retry layers.

## Repository layout

**One repository** (ADR-040): the applications, the infra and the docs live and are committed together. There are no submodules any more — a change that spans backend, frontend and data is one commit. The TypeScript projects are **npm workspaces** (`backend`, `frontend`, `packages/*`) with a single `package-lock.json` at the root: run `npm install` **at the root**, never inside a workspace. `data/` and `eval/` are Python projects beside them, outside the workspaces.

- `backend/` — Express + TypeScript API (the RAG **serving** orchestrator). The bulk of the runtime request logic.
- `frontend/` — Next.js 16 (App Router) + React 19 + Tailwind v4 chat UI.
- `packages/contract/` — `@murphy/contract`, what backend and frontend exchange at runtime: zod schemas and the types inferred from them, one module per contract imported by subpath (`@murphy/contract/messages`, `@murphy/contract/errors`, no barrel). Compiled by `tsc` to `dist/` (the root `postinstall` builds it). `packages/` only holds what crosses a runtime boundary between two workspaces.
- `data/` — Python/Kedro **ingestion** project that populates the databases (XML → parse → chunk → embed → Mongo/Qdrant/Neo4j). Runs offline, separately from the serving stack.
- `eval/` — Python evaluation harness (P2). Reads the databases through its own client; never imports `ragcore` (ADR-027).
- `docker-compose.base.yml` + `.dev.yml` / `.prod.yml` — the stack at the repo root: backend, frontend, MongoDB, Qdrant, Neo4j, and a HuggingFace TEI embedding service (GPU). The build context is the **repo root** (`backend/Dockerfile`, `frontend/Dockerfile`), because the apps share the root lockfile and the contract; the root `.dockerignore` keeps `.env*`, `node_modules`, `data/`, `eval/` and `docs/` out of it. Two Compose **profiles** share the same DB/embedding services: `ingest` (just the databases + TEI, for running `data/`'s `kedro run` against them) and `serve` (adds backend + frontend). The `data/` pipeline code itself still runs outside Docker, invoked manually.
- `docs/` — **cross-cutting docs only**: `pilotage/` (PM² steering), `product/` (vision, versions, ADRs), and `technical/ARCHITECTURE.md` (the system-level view). **Detailed technical documentation lives in each project's `docs/` folder** (`backend/docs/`, `frontend/docs/`, `data/docs/` — each with `README.md` index+operations, `ARCHITECTURE.md`, and `reference/`).

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

Dev ports: frontend `3000`, backend `5000`, Qdrant `6333`, Mongo `27017`, Neo4j `7474`/`7687`, embedding service `5001→80`. Dev mode mounts **only the sources** into the containers (`backend/src`, `frontend/src`, `frontend/public`) with hot-reload (`ts-node` watch for backend, `next dev` for frontend). Dependencies, app config and the built contract live in the images: after changing `packages/contract`, a `package.json` or an app config file, run `npm run serve:build`.

The embedding service requires an **NVIDIA GPU** (declared in `docker-compose.dev.yml`). Without one, run backend/frontend locally instead and point env vars at reachable services.

### Backend without Docker

Install once from the repo root: `npm install` (it also builds `packages/contract`). `npm run check` at the root runs everything the CI runs: contract build, backend type-check + lint + tests, frontend type-check + lint + build.

No env file is loaded: export the variables first (e.g. `set -a; . ../.env.dev; set +a`, then override the Docker hostnames such as `QDRANT_URL`). From `backend/` (or from the root with `-w backend`):

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

Jest coverage thresholds (`jest.config.js`: lines/statements 65%, functions 60%, branches 40%) are only checked with `npx jest --coverage` — plain `npm test` does not measure coverage. `src/server.ts` is excluded from coverage.

### Frontend without Docker

From `frontend/`: `npm run dev` (Turbopack), `npm run build`, `npm run type-check`, `npm run lint` (eslint, `--max-warnings=0`). TS path alias `@/*` → `frontend/src/*`.

## Architecture: the RAG request flow (serving)

The core pipeline lives in `backend/src/services/chatService.ts:createChatStream`. Trace it through:

1. **Extract question** — the last `user` message's text parts (`extractQuestionFromMessages`). Requests carry an AI SDK `messages` array, not a bare `question` string.
2. **Embed** (`ragService.embedQuestion`) → TEI embedding service.
3. **Retrieve** (`ragService.retrieveChunks`) → Qdrant top-K (`RETRIEVAL_TOP_K`, default 5).
4. **Fetch passages** (`ragService.fetchPassages`) → MongoDB `documents`, by `(identifier, owner_id)`. Each passage's text is cut out of its parent document's `content` between the payload's `char_start`/`char_end` (Unicode code points, converted to UTF-16 in `services/passages.ts`). A missing parent or out-of-range offsets raise a `CONTRACT_VIOLATION` `RagError` naming the chunk (ADR-039).
5. **Stream sources** — *before the LLM runs*, in ranking order: a `data-parentDocument` part (the whole document, **once** per document, before its first passage), then a `data-document` part per passage (with `highlightStart`/`highlightEnd`, UTF-16 offsets into the parent's `content`).
6. **Stream LLM** — context (the passage texts only, not the whole documents) is injected into the system prompt (`config.llm.systemPrompt`, French legal-assistant prompt, overridable via `SYSTEM_PROMPT` env), then `getInfraClients().llm.stream()` tokens are written as `text-delta` parts.
7. **Finish** — a `finish` part carries `ragTiming` metadata (per-stage latency in ms).

The stream is built with the Vercel **AI SDK** (`createUIMessageStream` / `pipeUIMessageStreamToResponse`). The message/part contract is `AppUIMessage` in `packages/contract/src/messages.ts` (`@murphy/contract/messages`), shared by both sides: the backend compiles against its types, the frontend validates incoming parts with its zod schemas (`useChat({ dataPartSchemas, messageMetadataSchema })`), so a change breaks both compilations at once. The custom data parts are `{ document: DocumentChunk; parentDocument: ParentDocument }` and metadata is `{ ragTiming }`.

### Two transports, same pipeline

`createChatStream` produces one stream consumed three ways:
- **WebSocket** (`routes/chatWebSocket.ts`, path `/api/v1/chat/ws`) — this is what the frontend actually uses (`useRagChat.ts` plugs the custom transport `lib/webSocketChatTransport.ts` into `@ai-sdk/react`'s `useChat`). One message in, stream of JSON parts out, socket closes.
- **POST `/api/v1/chat/streams`** (SSE) and **POST `/api/v1/chat/completions`** (drains the stream to a single JSON response) — `routes/chat.ts`. Useful for testing/non-streaming clients.

When changing the pipeline, change `createChatStream` once — all three paths inherit it.

**Errors and abort (ADR-041)**: an `error` part's `errorText` is a serialized `ChatError` `{ stage, code }` (`@murphy/contract/errors`; `types/rag.ts:toChatError`), never the raw message, which stays in the logs; the frontend shows the stage in a modal (`components/ui/Modal.tsx`). Closing the socket or the HTTP response raises the `AbortSignal` passed to `createChatStream`: the pipeline stops before the LLM, or cuts the LLM request (`llm.stream(messages, signal)`).

### Infrastructure clients (`backend/src/infra/`)

`EmbeddingClient` (TEI), `QdrantVectorClient`, `LLMProvider` (Mammouth.AI-style OpenAI-compatible API), and `MongoDbClient`. Each constructor takes its section of `config`; none reads the environment. `infra/clients.ts:initInfraClients(config)` creates them **once at boot**, before the server listens (connects Mongo, resolves the published Qdrant collection, builds the rest) and may refuse the boot. Requests reach them through `getInfraClients()` (throws if called before init); `closeInfraClients()` runs at graceful shutdown. Never `new` a client per request. Failures go through `types/rag.ts:toRagError`, which yields `RagError { stage, code }` with `code: 'TIMEOUT'` when the error's **type** name ends in `TimeoutError`.

### Cross-cutting backend conventions

- **API responses** go through `utils/response.ts:buildApiResponse(code, message, data?)` → `{ status: {code, message}, data?, meta: {timestamp, traceId} }`. Use it for all JSON responses for consistency.
- **Logging** is Pino (`utils/logger.ts`). Create a child logger per module: `rootLogger.child({ context: 'moduleName' })`. Logs are structured JSON.
- **Errors**: wrap async route handlers in `middleware/errorHandler.ts:asyncHandler`; `errorHandler` + `notFoundHandler` are registered last in `app.ts`.
- **Middleware order** (`app.ts`): requestLogger → helmet/rate-limit/CORS (`middleware/security.ts`) → body parsing → routes → error handlers. Chat payloads are checked by `validation/chatRequest.ts:parseChatRequest`, shared by the HTTP routes and the WebSocket. `middleware/streamRateLimiter.ts` gives each IP one stream budget (10/min by default), drawn by POST `/streams` and by each WebSocket message (`consumeStreamQuota`). `trust proxy` is `false` in `app.ts` (no proxy yet): set the hop count there once deployed behind one.
- **API base path** is `/api/v1`. Health is `/api/v1/health` (alias `/services`), with per-service latency; it reports `ok`/`degraded` (1 service down)/`down` (2+ down) and returns 503 when not ok.

## Ingestion pipeline (`data/`, Python/Kedro)

A Kedro project that ingests the DILA XML corpora (LEGI + the 5 case-law bases: CAPP, CASS, INCA, JADE, CONSTIT) and writes documents/vectors/graph into the same MongoDB / Qdrant / Neo4j the backend reads from. It runs **offline and out-of-band** — not part of the Docker serving stack, and the backend never calls into it.

**Full documentation: `data/docs/`** (architecture, node-by-node pipeline reference, data model, configuration, telemetry). Key structural facts:

- All pipeline logic lives in the **`ragcore` package, vendored at `data/src/ragcore/`** (hexagonal: `core/` domain + ports, `adapters/`, `application/`, `sources/`, `orchestration/kedro/`). `data/src/data/` is a thin Kedro shell that delegates to it (`settings.py` registers the hooks, `pipeline_registry.py` delegates the registry).
- One pipeline (`__default__` = `ingestion`): cleanup → nukeAll → connect → computeIdempotence → ingest (4-worker pool, saga Mongo→Qdrant→Neo4j-node) → resolveRelations (graph edges, pending-relations cache) → report. Runtime objects are `MemoryDataset`s injected by `TelemetryHooks.before_pipeline_run`.
- **Qdrant collection names are derived** (blake2b fingerprint of the workflow config: normalization + chunking + embedding), never hand-written. A run that ends `ok` publishes the pointer `MURPHY_META.meta_published_collection`, which the backend reads at boot (`backend/src/infra/collectionPointer.ts`).
- `data/conf/base/parameters.yml` is the tuning surface (`chunk_size: 384` chars / `chunk_overlap: 25`, normalization `v1`, `all-mpnet-base-v2` 768-dim). Env config is the **root `.env.dev` only** (read by absolute path — there is no `.env` in `data/`). `ENVIRONMENT=dev` gates `nuke_all`, the embedding switch (ADR-023) and Neo4j node hydration (ADR-022); the default is `prod` = locked.
- Run status (`ok`/`degraded`/`failed`) is derived from telemetry counters (completeness equation), not from exceptions. Only `ok` runs publish.

Tooling: `kedro run` (`--params source=cass,jade` to restrict), `kedro viz`, `ruff`, `pytest` (unit+golden need no DBs; `-m integration` uses testcontainers), `mypy` strict on `src/ragcore`.

## Configuration

Backend runtime config is environment-driven (see the `environment:` block in `docker-compose.base.yml` for the full list). Key vars: `MONGODB_URI/DATABASE/META_DB_NAME`, `QDRANT_URL`, `EMBEDDING_SERVICE_URL/EMBEDDING_MODEL`, `LLM_API_ENDPOINT/API_KEY/MODEL/TEMPERATURE/MAX_TOKENS`, `RETRIEVAL_TOP_K`, `RETRIEVAL_MIN_SCORE`, `SYSTEM_PROMPT`, plus rate-limit and CORS settings. **`backend/src/config.ts` is authoritative**: the only file that reads `process.env`, it loads and validates the environment once at boot into a typed `readonly` `config` (defaults included). An empty value counts as unset; a malformed number (`LLM_TEMPERATURE=abc`) stops the boot with the variable's name. `utils/configWarnings.ts:checkEnvironment()` then logs the missing required vars and the defaulted ones, derived from what `config.ts` actually read.

There is **one** env file for the whole system: `.env.dev` at the repo root (gitignored). Docker Compose feeds it to the serving stack, and the ingestion project reads the same file by absolute path (`ragcore/adapters/config/settings.py`) — a `.env` inside `data/` has no effect. One file so the TEI container and the pipeline can never disagree on the embedding model.

The embedding model and dimensions must match between ingestion and serving: the pipeline embeds with `all-mpnet-base-v2` (768-dim, Cosine), so the TEI service and `RETRIEVAL_*` settings on the backend must align with vectors of the same model/dimensionality. The Qdrant collection is never configured: the backend reads it from the pointer published by the last `ok` ingestion run (`MURPHY_META.meta_published_collection`) and **refuses to boot** when there is no pointer, when its `serving_contract_version` differs from the backend's `SERVING_CONTRACT_VERSION` (ADR-039), or when the collection doesn't exist.

Neo4j is provisioned in compose and written by the ingestion pipeline, but is not yet wired into the backend request path — it's reserved for future graph-based context enrichment.

---

<!-- Generated by init-claude-rules | https://github.com/lifedever/claude-rules -->

# Core Development Principles

## Attitude Toward Legacy Code

This is the most important rule: **Do not mimic the style and patterns of existing code in the project.** Always follow this specification.

- When modifying old code, refactor the parts you touch according to this specification. Do not perpetuate bad habits for the sake of "consistency"
- If old code has obvious design problems (God Class, deep nesting, hardcoding, excessive coupling), fix them while making changes
- Do not be afraid to change the structure of old code, as long as behavior remains unchanged
- If the refactoring scope is too large (cascading changes across more than 3 files), explain the plan before proceeding

## Hard Requirements for Code Quality

- A single function must not exceed 30 lines (excluding blank lines and comments); split if it does
- A single file must not exceed 300 lines; split by responsibility if it does
- Nesting depth must not exceed 3 levels (if/for/callback); reduce with early returns, extracted functions, etc.
- Function parameters must not exceed 4; use an object parameter if more are needed
- No commented-out code allowed; delete unused code instead of commenting it out
- No magic numbers or magic strings; extract them into named constants

## Naming

- Names must be semantic; the purpose should be clear from the name alone
- No meaningless names: `data1`, `temp`, `info`, `obj`, `result`, `item` (except loop variables)
- Boolean values use `is`/`has`/`can`/`should` prefixes: `isLoading`, `hasPermission`
- Function names start with a verb: `fetchUser`, `validateInput`, `calculateTotal`
- Constants in ALL_CAPS_SNAKE_CASE: `MAX_RETRY_COUNT`, `API_BASE_URL`
- Event handler functions use `handle` prefix: `handleClick`, `handleSubmit`

## Architecture Principles

- **Single Responsibility**: One function does one thing, one file owns one domain
- **Separation of Concerns**: UI contains no business logic, business logic contains no UI code, data access is a separate layer
- **Unidirectional Dependencies**: Upper layers depend on lower layers, never the reverse. UI -> Business Logic -> Data Layer
- **Program to Interfaces**: Modules communicate through interfaces/protocols, not concrete implementations
- **Composition Over Inheritance**: Use composition unless there is a clear is-a relationship

## Error Handling

- Perform defensive validation only at system boundaries (user input, external API responses, file I/O)
- Internal function calls trust parameter types; no redundant validation
- Error messages should be human-friendly and include context (which operation failed, what values were passed)
- Async operations must have error handling; no bare Promises or unhandled async calls
- Do not wrap the entire function body in try-catch; only wrap the specific operations that may fail

## Avoid Over-Engineering

- Solve only the current problem; do not add abstractions for hypothetical future requirements
- Three lines of duplicated code are better than a premature abstraction
- Do not create utility functions for logic that is used only once
- Do not add unnecessary intermediate layers, wrappers, or adapters
- Add configuration and options only when flexibility is genuinely needed

## Output Requirements

- Always respond in French
- Get straight to the point; no pleasantries or preamble
- Only output information directly relevant to the current task; do not repeat what the user has already said

# Git Conventions

## Commit Rules

- Do not commit code automatically unless explicitly requested
- Ensure the code runs correctly before committing
- Commit directly to main/master to stay agile

## Commit Message Format

```
<type>(<scope>): <subject>
```

A space follows the colon. Type values:

| type | Purpose |
|------|---------|
| feat | New feature |
| fix | Bug fix |
| docs | Documentation or comments |
| style | Code formatting (no runtime impact) |
| refactor | Refactoring (not a new feature or bug fix) |
| perf | Performance optimization |
| test | Adding tests |
| chore | Build process or tooling changes |

Use a list when there are more than two key points:

```
feat(web): implement email verification workflow

- Add email verification token generation service
- Create verification email template with dynamic links
- Add API endpoint for token validation
```

# Python Guidelines

## Core Principles

- Follow PEP 8; use ruff for formatting and linting
- Type annotations: all public function parameters and return values must have type annotations
- Use `pathlib.Path` instead of `os.path`
- Use f-strings instead of `format()` and `%`

## Naming

- Classes: `PascalCase` (`UserService`, `DataProcessor`)
- Functions and variables: `snake_case` (`get_user_by_id`, `is_valid`)
- Constants: `UPPER_SNAKE_CASE` (`MAX_RETRY_COUNT`)
- Private members: single underscore prefix `_internal_method`
- No double-underscore name mangling (`__private`) unless there is a clear reason

## Type Annotations

```python
# 禁止
def process(data, config):
    ...

# 正确
def process(data: list[dict[str, Any]], config: ProcessConfig) -> ProcessResult:
    ...
```

- Use `X | None` instead of `Optional[X]` (Python 3.10+)
- Use `list[str]` instead of `List[str]` (Python 3.9+)
- Use `TypeAlias` or `TypedDict` for complex types
- Use `Protocol` to define structural subtypes instead of ABCs

## Error Handling

- Catch specific exceptions; no bare `except:` or `except Exception:`
- Custom business exceptions should inherit from a specific built-in exception class
- Use `raise ... from e` to preserve the exception chain

```python
# 禁止
try:
    result = call_api()
except:
    pass

# 正确
try:
    result = call_api()
except httpx.TimeoutException as e:
    raise ServiceUnavailableError(f"API timeout: {e.url}") from e
```

## Async

- Use `async/await` for asynchronous code; do not mix threads and coroutines
- Use `asyncio.TaskGroup` for concurrent execution (Python 3.11+)
- Use `contextlib.asynccontextmanager` to manage async resources

## Data Classes

- Use `dataclass` or `pydantic.BaseModel` for simple data containers
- Use `@dataclass(frozen=True)` for immutable data
- Use `pydantic.BaseSettings` for configuration objects

## Project Structure

- Use `pyproject.toml` for project configuration (not `setup.py`)
- Use pytest for testing; place configuration in `[tool.pytest]` within `pyproject.toml`
- Use `uv` or `poetry` for dependency management

# TypeScript Guidelines

## Type System

- No `any`. Use `unknown` when the type is uncertain, then narrow with type guards
- Use `interface` for object shapes; use `type` for unions / intersections / mapped types
- Public functions must have explicit return types; internal functions may rely on inference
- Mark properties and parameters that won't be mutated with `readonly`
- Leverage built-in utility types: `Partial<T>`, `Pick<T, K>`, `Omit<T, K>`, `Record<K, V>`
- Generic parameter names should be meaningful: `TItem` rather than bare `T` (single generic parameter excepted)

```typescript
// 禁止
function parse(data: any): any { ... }

// 正确
function parse(data: unknown): ParseResult { ... }
```

## Naming

- Types and interfaces: `PascalCase` (`UserProfile`, `ApiResponse`)
- Variables and functions: `camelCase` (`getUserById`, `isValid`)
- Constants: `UPPER_CASE` (`MAX_RETRY_COUNT`)
- Enum members: `PascalCase` (`Status.Active`)
- Generic parameters: single uppercase letter or `T` prefix (`T`, `TKey`, `TValue`)

## Module Organization

- One primary export per file (a component, a class, or a group of closely related functions)
- Place type definitions at the top of the file that uses them; shared cross-file types go in a `types/` directory
- Do not use `index.ts` barrel exports -- they cause circular dependencies and tree-shaking issues; import directly from source files
- Separate `import type` from value imports

```typescript
import type { UserProfile } from './types/user'
import { formatDate } from './utils/date'
```

## Functions

- Prefer arrow functions; use `function` only when `this` binding is needed
- Prefer `async/await`; do not chain more than 2 levels of `.then()`
- Handle errors with specific types; do not `catch(e: any)`

```typescript
// 禁止
fetchData().then(res => process(res)).then(data => save(data)).catch(e => console.log(e))

// 正确
try {
  const res = await fetchData()
  const data = process(res)
  await save(data)
} catch (error) {
  if (error instanceof NetworkError) {
    showNetworkError(error.message)
  }
  throw error
}
```

## Prohibited Patterns

- No `// @ts-ignore` or `// @ts-expect-error` (unless accompanied by a comment explaining why)
- No `as` type assertions (unless narrowing from `unknown` with good reason)
- No `!` non-null assertions (use optional chaining `?.` or early null checks instead)
- No `enum` (use `as const` objects or union types instead to avoid runtime overhead)

```typescript
// 禁止
enum Status { Active, Inactive }

// 正确
const Status = { Active: 'active', Inactive: 'inactive' } as const
type Status = typeof Status[keyof typeof Status]
```

# React Guidelines

## Basic Component Rules

- Use only function components; class components are forbidden
- A single component file must not exceed 200 lines
- Components are responsible only for UI; extract business logic into custom hooks
- Complex expressions in JSX are forbidden; extract them into variables or functions
- A file should export only one component (except small helper components)

## State Management

- Use `useState` for component-local state
- Use `useReducer` for complex state logic
- Keep state as close to where it is used as possible; do not lift state unnecessarily
- Use Context (for small amounts of global state) or Zustand/Jotai (for complex scenarios) for cross-component sharing
- Prop drilling beyond 2 levels is forbidden

```tsx
// Forbidden: prop drilling
<GrandParent user={user}>
  <Parent user={user}>
    <Child user={user} />  // 3 levels deep
  </Parent>
</GrandParent>

// Correct: Context
const UserContext = createContext<User | null>(null)
const useUser = () => {
  const user = useContext(UserContext)
  if (!user) throw new Error('useUser must be used within UserProvider')
  return user
}
```

## Hook Rules

- Custom hook file names must have the `use` prefix: `useAuth.ts`
- A hook should do one thing only
- `useEffect` must have a correct dependency array; suppressing with `// eslint-disable-next-line` is forbidden
- `useEffect` with side effects must return a cleanup function
- Passing an async function directly to `useEffect` is forbidden

```typescript
// Forbidden
useEffect(async () => {
  const data = await fetchData()
  setData(data)
}, [])

// Correct
useEffect(() => {
  const controller = new AbortController()
  const load = async () => {
    try {
      const data = await fetchData({ signal: controller.signal })
      setData(data)
    } catch (error) {
      if (!controller.signal.aborted) setError(error)
    }
  }
  load()
  return () => controller.abort()
}, [])
```

## Performance

- Use `React.memo` only on components with actual performance issues; do not use it preemptively
- Use `useMemo` / `useCallback` only in the following scenarios:
  - Computationally expensive derived values
  - Dependencies of other hooks
  - Props passed to children wrapped with `React.memo`
- Lists must have stable, unique `key` values; using index is forbidden
- Use virtualization for large lists (`react-virtual` / `react-window`)

## Props

- Define with TypeScript interfaces, named `XxxProps`
- Prefer primitive types over objects for props
- Name callback props with `onXxx`: `onClick`, `onSubmit`

```typescript
interface UserCardProps {
  name: string
  email: string
  onEdit: (id: string) => void
}
```

## Error Handling

- Page-level components must have an Error Boundary
- Async operations must handle loading / error / empty states
- Error messages should be user-friendly; log raw errors to the console

## Styling

- Prefer Tailwind CSS
- Use CSS Modules or `clsx`/`cn` for class name concatenation when dynamic styles are needed
- Inline style objects are forbidden (unless the values are truly dynamically computed)
- `!important` is forbidden
