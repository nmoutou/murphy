// ⚠️ SHARED CONTRACT — keep in sync with murphy-backend: src/types/messages.ts
// This type defines the WebSocket/SSE message+part contract between the two repos.
// There is no compile-time enforcement across repos; changes here MUST be mirrored there.
import type { UIMessage } from 'ai';

export type DocumentChunk = {
  chunkId: string;
  title?: string;
  type?: string;
  score: number;
};

export type RagTiming = {
  embeddingMs: number;
  retrievalMs: number;
  docFetchMs?: number;
  totalMs: number;
  llmMs?: number;
};

export type AppMessageMetadata = {
  ragTiming?: RagTiming;
};

export type AppUIMessage = UIMessage<AppMessageMetadata, { document: DocumentChunk }>;
