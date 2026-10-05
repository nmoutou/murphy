# Murphy — backend

Express + TypeScript API — the RAG **serving** orchestrator for the Murphy system.

Stateless by design: every request recomputes the full pipeline (embed → hybrid search →
fetch → stream LLM). No conversational history, no retries.

## Develop

Dependencies are installed **from the repository root** (`npm install`), which also
builds the shared contract (`packages/contract`). Then, from this directory:

```bash
npm run dev          # ts-node src/server.ts
npm run dev:watch    # nodemon + ts-node (auto-restart)
npm run type-check
npm run lint
npm test
```

Requires reachable MongoDB, OpenSearch (with the index written by `data/`), and a TEI
embedding service (see env vars in `src/config.ts`). For the full stack including those
services, run `npm run up` at the repository root.

The stream contract (`AppUIMessage`) is imported from `@murphy/contract/messages`,
shared with the frontend: see [`docs/technical/backend/ARCHITECTURE.md`](../docs/technical/backend/ARCHITECTURE.md).
