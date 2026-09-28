# CLAUDE.md

Guidance for Claude Code in this repository.

## What this is

Murphy is a RAG chatbot over French legal documents (LEGIFRANCE / DILA data). The backend embeds a question, searches legal-document chunks, reads the matching passages, and streams an LLM answer to the frontend along with its sources.

The backend is **stateless by design**: every request recomputes the whole pipeline, with no conversation history, no cache and no automatic retry (fail fast with a clear error). Think twice before adding caching, sessions or retries.

## Repository layout

One repository (ADR-040). The TypeScript projects are **npm workspaces** (`backend`, `frontend`, `packages/*`) with a single root `package-lock.json`: run `npm install` **at the root only** (its `postinstall` builds the contract).

- `backend/` — Express + TypeScript: the RAG serving pipeline.
- `frontend/` — Next.js 16 (App Router), React 19, Tailwind v4.
- `packages/contract/` — `@murphy/contract`: the zod schemas, and the types inferred from them, that backend and frontend exchange at runtime. One module per subpath (`@murphy/contract/messages`, `@murphy/contract/errors`), no barrel; compiled by `tsc` to `dist/`. Only what crosses a runtime boundary between workspaces belongs in `packages/`.
- `data/` — Python/Kedro ingestion (XML → chunks → Mongo/Qdrant/Neo4j), run offline. It shares the databases with the backend, never code.
- `eval/` — Python evaluation harness; never imports `ragcore` (ADR-027).
- `docs/` — cross-cutting docs only: `pilotage/` (steering: status, backlog, log), `product/` (vision, versions, `ADR/`), `technical/ARCHITECTURE.md`. Each project documents itself in its own `docs/` (`README.md` = index + operations, `ARCHITECTURE.md`).

## Commands

`npm run check` at the root runs what the CI runs for TypeScript: contract build, backend type-check + lint + tests, frontend type-check + lint + tests + format check + build. The CI's `python` job checks `data/` separately (see Ingestion). `next build` rewrites `frontend/next-env.d.ts`: restore it with `git checkout` afterwards.

Both ESLint configs enforce the size limits of the rules below: 300 lines per file (200 per frontend `.tsx`), 30 lines per function (blank lines and comments excluded), depth 3, 4 parameters, complexity 10, and `no-magic-numbers`. Tests are exempt from the function length and magic number rules. Shared HTTP statuses live in `backend/src/utils/httpStatus.ts`.

### Docker stack

The root scripts wrap Docker Compose and need `.env.dev` at the root (gitignored). It is the **only** env file of the system: Compose feeds it to the stack, and `data/` reads it by absolute path.

```bash
npm run serve:up | serve:watch | serve:build | serve:down   # DBs + TEI + backend + frontend (aliases: up, watch, build)
npm run ingest:up | ingest:watch | ingest:down | ingest:logs | ingest:status   # DBs + TEI, for data/'s kedro run
npm run down | restart | logs | status   # both profiles
```

- Always stop with `npm run down`: a raw `docker compose down` without `--profile` reports success and leaves profiled services running.
- `mongo`, `qdrant` and `neo4j` have no profile; `backend`/`frontend` are `serve` only; `embedding-service` (TEI, needs an NVIDIA GPU) is in both.
- Dev ports: frontend `3000`, backend `5000`, Qdrant `6333`, Mongo `27017`, Neo4j `7474`/`7687`, TEI `5001`.
- Dev mounts only the sources (`backend/src`, `frontend/src`, `frontend/public`) with hot reload. Dependencies, app configs and the built contract live in the images: run `npm run serve:build` after changing `packages/contract`, a `package.json` or an app config.
- The build context is the repo root (`backend/Dockerfile`, `frontend/Dockerfile`); the root `.dockerignore` keeps `.env*`, `node_modules`, `data/`, `eval/` and `docs/` out.
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

1. **Extract the question** — the text parts of the last `user` message (requests carry an AI SDK `messages` array).
2. **Embed** → TEI.
3. **Retrieve** → Qdrant top-K (`RETRIEVAL_TOP_K`, default 5).
4. **Fetch passages** → Mongo `documents`, by `(identifier, owner_id)`. Each passage is cut out of its parent's `content` between the payload's `char_start`/`char_end` (code points, converted to UTF-16 in `services/passages.ts`). A missing parent or out-of-range offsets raise a `CONTRACT_VIOLATION` `RagError` (ADR-039).
5. **Stream the sources**, before the LLM, in ranking order: a `data-parentDocument` part once per document, then a `data-document` part per passage (`highlightStart`/`highlightEnd`, UTF-16).
6. **Stream the LLM** — only the passage texts go into the system prompt (`config.llm.systemPrompt`, overridable by `SYSTEM_PROMPT`); tokens become `text-delta` parts.
7. **Finish** — a `finish` part with the `ragTiming` metadata.

The stream contract is `AppUIMessage` (`@murphy/contract/messages`): the backend compiles against it, the frontend validates incoming parts with the same zod schemas: the `data-*` parts in `lib/webSocketChatTransport.ts` (ai 6.0.x never applies `useChat`'s `dataPartSchemas`: it looks them up by part type, `data-document`, not by name), the metadata in `useChat({ messageMetadataSchema })`. A change breaks both compilations at once.

One stream, three transports — change `createChatStream` once:
- **WebSocket** `/api/v1/chat/ws` (`routes/chatWebSocket.ts`), the one the frontend uses (`hooks/useRagChat.ts` plugs `lib/webSocketChatTransport.ts` into `useChat`);
- **POST** `/api/v1/chat/streams` (SSE) and `/api/v1/chat/completions` (JSON) — `routes/chat.ts`.

**Errors and abort (ADR-041)**: an `error` part's `errorText` is a serialized `ChatError` `{ stage, code }` (`@murphy/contract/errors`, built by `types/rag.ts:toChatError`), never the raw message, which stays in the logs. The frontend names the failed stage in a modal. Closing the socket or the HTTP response raises the `AbortSignal`: the pipeline stops before the LLM, or cuts the LLM request.

### Backend conventions

- **Config**: `src/config.ts` is the only reader of `process.env`. It validates the environment once at boot into a typed `readonly` `config` (an empty value counts as unset; a malformed number stops the boot). `utils/configWarnings.ts` logs the missing and defaulted variables. The full list is the `environment:` block of `docker-compose.base.yml` (note: Compose passes `EMBEDDING_MODEL` to the backend as `EMBEDDING_MODEL_NAME`).
- **Infra clients** (`src/infra/`): `EmbeddingClient`, `QdrantVectorClient`, `LLMProvider` (OpenAI-compatible API), `MongoDbClient`; each takes its section of `config`. `initInfraClients(config)` builds them once at boot and may refuse the boot; requests use `getInfraClients()`. Never create a client per request. Failures go through `types/rag.ts:toRagError` → `RagError { stage, code }` (`TIMEOUT` when the error's type name ends in `TimeoutError`).
- **Qdrant collection**: never configured. The backend reads the pointer `MURPHY_META.meta_published_collection`, published by the last `ok` ingestion run, and refuses to boot when it is missing, when its `serving_contract_version` differs from `SERVING_CONTRACT_VERSION` (ADR-039), or when the collection does not exist. The embedding model must match the ingestion's (`all-mpnet-base-v2`, 768 dimensions, cosine).
- **HTTP**: base path `/api/v1`. JSON responses go through `utils/response.ts:buildApiResponse(code, message, data?)`. Async handlers are wrapped in `asyncHandler`; `notFoundHandler` and `errorHandler` come last in `app.ts`, after requestLogger → security (helmet, rate limit, CORS) → body parsing → routes.
- **Chat requests**: validated by `validation/chatRequest.ts:parseChatRequest` (HTTP and WebSocket). One stream budget per IP (10/min by default, `middleware/streamRateLimiter.ts`), shared by `/streams`, `/completions` and WebSocket messages. `trust proxy` is `false` in `app.ts` until a proxy is deployed.
- **Health**: `/api/v1/health` (alias `/api/v1/health/services`) probes TEI, Qdrant and Mongo: `ok`, `degraded` (1 down) or `down` (2+), 503 unless `ok`.
- **Logging**: Pino, one child logger per module (`rootLogger.child({ context: 'moduleName' })`).
- Neo4j is written by the ingestion but not yet read by the backend.

### Frontend conventions

- Colors are Tailwind classes from the `@theme` of `styles/globals.css` (`bg-secondary`, `text-tertiary`…): no theme context, no inline styles.
- `components/ui/Modal.tsx` is the generic modal (native `<dialog>`); `app/error.tsx` is the page's Error Boundary.
- Icons are decorative; an icon button carries its accessible name (`ButtonIcon`, `label`).

## Ingestion (`data/`, Python/Kedro)

Full documentation: `data/docs/`. Key facts:

- The logic lives in the `ragcore` package (`data/src/ragcore/`, hexagonal); `data/src/data/` is a thin Kedro shell delegating to it.
- One pipeline (`__default__` = `ingestion`): cleanup → nukeAll → connect → computeIdempotence → ingest (saga Mongo → Qdrant → Neo4j node) → resolveRelations → report.
- Qdrant collection names are derived (a fingerprint of the workflow config), never hand-written. The run status (`ok`/`degraded`/`failed`) comes from telemetry counters; only `ok` runs publish the pointer.
- Tuning: `data/conf/base/workflow/parameters.yml` (chunks of 384 chars, overlap 25, `all-mpnet-base-v2`). `ENVIRONMENT=dev` unlocks `nuke_all`, the embedding switch (ADR-023) and Neo4j node hydration (ADR-022); the default `prod` locks them.
- Tooling: `kedro run` (`--params source=cass,jade` to restrict), `ruff`, `pytest` (`-m integration` uses testcontainers), `mypy` strict on `src/ragcore`.
- CI (`python` job, from `data/`): `uv sync --locked --extra dev`, then `uv run --locked` `ruff check .`, `ruff format --check .`, `mypy`, `pytest` (unit tests only: `addopts` excludes `integration`). Needs no `.env.dev` and no database.

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
