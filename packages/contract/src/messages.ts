/**
 * The stream contract between backend and frontend: the AI SDK message, its custom
 * data parts and its metadata. The backend writes these parts (WebSocket and SSE), the
 * frontend validates them on arrival with the same schemas (`useChat`), and both
 * compile against the types inferred here: a change breaks both sides at once.
 */

import type { UIMessage } from 'ai';
import { z } from 'zod';

/**
 * One retrieved passage (ADR-039 §5). `content.slice(highlightStart, highlightEnd)`
 * of its `ParentDocument`, found by `identifier`, gives the passage text.
 * `title` and `type` repeat the parent's until the frontend reads `ParentDocument`.
 */
export const documentChunkSchema = z.object({
  chunkId: z.string(),
  identifier: z.string(),
  /** UTF-16 offsets into the parent's `content`, as JavaScript strings count */
  highlightStart: z.number().int().nonnegative(),
  highlightEnd: z.number().int().nonnegative(),
  score: z.number(),
  title: z.string().optional(),
  type: z.string().optional(),
});

/** The whole document a passage comes from, sent once per response, before its passages */
export const parentDocumentSchema = z.object({
  identifier: z.string(),
  title: z.string(),
  type: z.string().optional(),
  content: z.string(),
});

/** Per-stage latency of the pipeline, in milliseconds */
export const ragTimingSchema = z.object({
  embeddingMs: z.number(),
  retrievalMs: z.number(),
  docFetchMs: z.number().optional(),
  totalMs: z.number(),
  llmMs: z.number().optional(),
});

export const appMessageMetadataSchema = z.object({
  ragTiming: ragTimingSchema.optional(),
});

/** Keyed by data part name: `document` travels as a `data-document` part */
export const appDataPartSchemas = {
  document: documentChunkSchema,
  parentDocument: parentDocumentSchema,
};

export type DocumentChunk = z.infer<typeof documentChunkSchema>;
export type ParentDocument = z.infer<typeof parentDocumentSchema>;
export type RagTiming = z.infer<typeof ragTimingSchema>;
export type AppMessageMetadata = z.infer<typeof appMessageMetadataSchema>;

export type AppUIMessage = UIMessage<
  AppMessageMetadata,
  { document: DocumentChunk; parentDocument: ParentDocument }
>;
