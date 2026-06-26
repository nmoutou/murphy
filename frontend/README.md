# murphy-frontend

Next.js 16 (App Router) + React 19 + Tailwind v4 chat UI for the Murphy RAG system.

Talks to `murphy-backend` over a custom WebSocket transport (`@ai-sdk/react` `useChat`).

## Develop

```bash
npm install
npm run dev      # Turbopack
npm run build
npm run lint
```

Set `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL` to point at the backend.

> **Note:** `src/types/messages.ts` is a shared contract duplicated in `murphy-backend`.
> Keep both copies in sync.
