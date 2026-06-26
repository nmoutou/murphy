/**
 * RAG Pipeline Types
 * Shared types for embedding, retrieval, and LLM operations
 */

/**
 * RAG Error with stage information
 */
export class RagError extends Error {
  constructor(
    public readonly stage: 'embedding' | 'retrieval' | 'llm',
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = 'RagError';
    Object.setPrototypeOf(this, RagError.prototype);
  }
}

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
    [key: string]: any;
  };
}

/**
 * Embedding response from TEI service
 * 768 dimensions (all-mpnet-base-v2)
 */
export type EmbeddingVector = number[];


