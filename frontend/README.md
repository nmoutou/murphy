# Murphy — frontend

Next.js 16 (App Router) + React 19 + Tailwind v4 chat UI for the Murphy RAG system.

Talks to the backend over a custom WebSocket transport (`@ai-sdk/react` `useChat`).

## Develop

Dependencies are installed **from the repository root** (`npm install`), which also
builds the shared contract (`packages/contract`). Then, from this directory:

```bash
npm run dev         # Turbopack
npm run build
npm run type-check
npm run lint        # eslint, no warning allowed
npm run format      # prettier --write src (format:check runs in CI)
```

Set `NEXT_PUBLIC_API_URL` to the backend base URL (default `http://localhost:5000`);
the chat WebSocket URL is derived from it (`src/lib/chatSocketUrl.ts`).

The stream contract (`AppUIMessage`) is imported from `@murphy/contract/messages`,
shared with the backend: see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
