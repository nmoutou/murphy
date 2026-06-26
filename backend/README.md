# murphy-backend

Express + TypeScript API — the RAG **serving** orchestrator for the Murphy system.

Stateless by design: every request recomputes the full pipeline (embed → retrieve →
fetch → stream LLM). No conversational history, no retries.

## Develop

```bash
npm install
npm run dev          # ts-node src/server.ts
npm run dev:watch    # nodemon + ts-node (auto-restart)
npm run type-check
npm run lint
npm test
```

Requires reachable MongoDB, Qdrant, and a TEI embedding service (see env vars in
`src/utils/configWarnings.ts`). For the full stack including those services, use the
`murphy-infra` repo.

> **Note:** `src/types/messages.ts` is a shared contract duplicated in `murphy-frontend`.
> Keep both copies in sync.
