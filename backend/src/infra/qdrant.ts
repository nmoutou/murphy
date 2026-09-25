/**
 * Qdrant Vector Database Client
 * Handles semantic search over the collection resolved at boot
 */

import { QdrantClient } from '@qdrant/qdrant-js';
import type { EmbeddingVector, RagFailure, RetrievedChunk } from '../types/rag';
import { logger } from '../utils/logger';
import { contractViolation, toRagError } from '../types/rag';

export interface QdrantVectorClientOptions {
  readonly url: string;
  /** The collection published by the last `ok` ingestion run (`infra/collectionPointer.ts`) */
  readonly collection: string;
  readonly minScore: number;
}

const SEARCH_FAILURE: RagFailure = { stage: 'retrieval', code: 'SEARCH_FAILED', operation: 'search Qdrant' };

type Payload = Record<string, unknown> | null | undefined;

interface ScoredPoint {
  readonly id: string | number;
  readonly score: number;
  readonly payload?: Payload;
}

const readString = (payload: Payload, field: string): string | undefined => {
  const value = payload?.[field];
  return typeof value === 'string' ? value : undefined;
};

const readInteger = (payload: Payload, field: string): number | undefined => {
  const value = payload?.[field];
  return typeof value === 'number' && Number.isInteger(value) ? value : undefined;
};

/**
 * Checks a point's payload against the serving contract (ADR-039 §2)
 * @throws RagError `CONTRACT_VIOLATION` naming the point when a field is missing
 */
export const toRetrievedChunk = ({ id, score, payload }: ScoredPoint): RetrievedChunk => {
  const chunkId = readString(payload, 'chunk_id');
  const identifier = readString(payload, 'identifier');
  const ownerId = readString(payload, 'owner_id');
  const charStart = readInteger(payload, 'char_start');
  const charEnd = readInteger(payload, 'char_end');
  if (!chunkId || !identifier || !ownerId || charStart === undefined || charEnd === undefined) {
    throw contractViolation(
      `Qdrant point ${chunkId ?? String(id)} lacks chunk_id, identifier, owner_id, char_start or char_end`
    );
  }
  return { chunkId, identifier, ownerId, charStart, charEnd, score, type: readString(payload, 'type_document') };
};

/**
 * Qdrant client for vector similarity search
 */
export class QdrantVectorClient {
  private readonly client: QdrantClient;

  constructor(private readonly options: QdrantVectorClientOptions) {
    this.client = new QdrantClient({ url: options.url });
  }

  /**
   * Search for similar vectors
   * @param vector Embedding vector of the question
   * @param topK Number of results to return
   * @returns The chunks ranked by similarity, their payload checked against the contract
   * @throws RagError with stage='retrieval'
   */
  async searchVectors(vector: EmbeddingVector, topK: number): Promise<RetrievedChunk[]> {
    const startTime = Date.now();
    const { collection, minScore } = this.options;
    logger.info({ vectorDim: vector.length, topK, collection }, 'Qdrant search started');

    let points: ScoredPoint[];
    try {
      points = await this.client.search(collection, {
        vector,
        limit: topK,
        score_threshold: minScore,
        with_payload: true,
      });
    } catch (error) {
      const ragError = toRagError(SEARCH_FAILURE, error);
      logger.error({ err: error, durationMs: Date.now() - startTime }, ragError.message);
      throw ragError;
    }

    // Outside the `try`: a contract violation must not be reported as a failed search
    const chunks = points.map(toRetrievedChunk);
    logger.info({ resultCount: chunks.length, minScore, durationMs: Date.now() - startTime }, 'Qdrant search completed');
    return chunks;
  }
}
