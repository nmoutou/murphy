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

const CONTRACT_VIOLATION_CODE = 'CONTRACT_VIOLATION';

/**
 * The databases do not hold what the serving contract (ADR-039) says. Never skipped
 * silently: a wrong passage in the LLM context is worse than a visible error.
 */
export const contractViolation = (message: string): RagError =>
  new RagError('retrieval', CONTRACT_VIOLATION_CODE, `Serving contract violated (ADR-039): ${message}`);

/** The key of a document in MongoDB `documents` (ADR-039 §2) */
export interface DocumentKey {
  readonly identifier: string;
  readonly ownerId: string;
}

/** A `Map` key for a `DocumentKey`: JSON keeps the two parts apart whatever they contain */
export const serializeDocumentKey = ({ identifier, ownerId }: DocumentKey): string =>
  JSON.stringify([identifier, ownerId]);

/**
 * A Qdrant hit, its payload checked against the serving contract (ADR-039 §2).
 * `charStart`/`charEnd` count Unicode code points in the parent's `content`.
 */
export interface RetrievedChunk extends DocumentKey {
  readonly chunkId: string;
  readonly charStart: number;
  readonly charEnd: number;
  readonly score: number;
  /** `type_document`, when the source sets it */
  readonly type?: string;
}

/** A parent document as the ingestion stored it in MongoDB `documents` */
export interface StoredDocument extends DocumentKey {
  readonly title: string;
  readonly content: string;
}

/** A retrieved chunk joined to its parent document, with its text cut out */
export interface Passage {
  readonly chunk: RetrievedChunk;
  readonly document: StoredDocument;
  readonly text: string;
  /** UTF-16 offsets of `text` in `document.content` */
  readonly highlightStart: number;
  readonly highlightEnd: number;
}

/**
 * Embedding vector from the TEI service; its length depends on the configured model
 */
export type EmbeddingVector = number[];
