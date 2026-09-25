/**
 * RAG Pipeline Types
 * Shared types for embedding, retrieval, and LLM operations
 */

export type RagStage = 'embedding' | 'retrieval' | 'llm';

/**
 * RAG Error with stage information
 */
export class RagError extends Error {
  constructor(
    public readonly stage: RagStage,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = 'RagError';
    Object.setPrototypeOf(this, RagError.prototype);
  }
}

/** How one infrastructure call fails, when the cause is not a timeout */
export interface RagFailure {
  readonly stage: RagStage;
  readonly code: string;
  /** Completes "Failed to …", e.g. `generate embeddings` */
  readonly operation: string;
}

const TIMEOUT_CODE = 'TIMEOUT';
/**
 * `TimeoutError` (`AbortSignal.timeout`), `QdrantClientTimeoutError`,
 * `MongoNetworkTimeoutError`, `MongoOperationTimeoutError`
 */
const TIMEOUT_ERROR_NAME_SUFFIX = 'TimeoutError';

/**
 * Reads `name` or `message` on any thrown object. Duck-typed rather than
 * `instanceof Error`: a `DOMException` from another realm (Jest's sandbox, say)
 * carries both without passing that test.
 */
const readErrorField = (error: unknown, field: 'name' | 'message'): string | undefined => {
  if (typeof error !== 'object' || error === null) return undefined;
  const value: unknown = Reflect.get(error, field);
  return typeof value === 'string' ? value : undefined;
};

/**
 * Wraps a failed infrastructure call into a `RagError`. The code is `TIMEOUT`
 * when the error type says so, the failure's own code otherwise.
 */
export const toRagError = (failure: RagFailure, error: unknown): RagError => {
  const isTimeout = readErrorField(error, 'name')?.endsWith(TIMEOUT_ERROR_NAME_SUFFIX) ?? false;
  const cause = readErrorField(error, 'message') ?? String(error);
  return new RagError(failure.stage, isTimeout ? TIMEOUT_CODE : failure.code, `Failed to ${failure.operation}: ${cause}`);
};

/**
 * Raw document from MongoDB
 */
export interface Document {
  _id?: { toString(): string };
  chunkId: string;
  content?: string;
  title?: string;
  type?: string;
  score?: number;
  [key: string]: unknown;
}

/**
 * Search result from Qdrant
 */
export interface SearchResult {
  id: string;
  similarity: number;
  payload: {
    chunkId?: string;
    title?: string;
    type?: string;
    [key: string]: unknown;
  };
}

/**
 * Embedding vector from the TEI service; its length depends on the configured model
 */
export type EmbeddingVector = number[];
