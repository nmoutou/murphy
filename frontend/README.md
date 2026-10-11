# Murphy — frontend

Next.js 16 (App Router) + React 19 + Tailwind v4 search UI for Murphy: a page of ranked
documents, each opened in a Dockview tab with its passage highlighted (ADR-032). It calls
the backend's search API over HTTP; state lives in Zustand stores.

## Develop

Dependencies are installed **from the repository root** (`npm install`), which also
builds the shared contract (`packages/contract`). Then, from this directory:

```bash
npm run dev         # Turbopack
npm run build
npm run type-check
npm run lint        # eslint, no warning allowed; enforces the size limits of CLAUDE.md
npm test            # vitest run: src/__tests__/, Testing Library on jsdom
npm run format      # prettier --write src (format:check runs in CI)
```

Set `NEXT_PUBLIC_API_URL` to the backend origin (default `http://localhost:5000`); the
frontend appends `/api/v1` (`src/lib/api/apiUrl.ts`).

The API contract is imported from `@murphy/contract/search`, shared with the backend:
see [`docs/technical/frontend/ARCHITECTURE.md`](../docs/technical/frontend/ARCHITECTURE.md).
