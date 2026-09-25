/**
 * Qdrant Vector Database Client
 * Handles semantic search over the collection resolved at boot
 */

import { QdrantClient } from '@qdrant/qdrant-js';
import type { EmbeddingVector, RagFailure, SearchResult } from '../types/rag';
import { logger } from '../utils/logger';
import { toRagError } from '../types/rag';

export interface QdrantVectorClientOptions {
  readonly url: string;
  /** The collection published by the last `ok` ingestion run (`infra/collectionPointer.ts`) */
  readonly collection: string;
  readonly minScore: number;
}

const SEARCH_FAILURE: RagFailure = { stage: 'retrieval', code: 'SEARCH_FAILED', operation: 'search Qdrant' };

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
   * @returns Array of search results ranked by similarity
   * @throws RagError with stage='retrieval'
   */
  async searchVectors(vector: EmbeddingVector, topK: number): Promise<SearchResult[]> {
    const startTime = Date.now();
    const { collection, minScore } = this.options;
    logger.info({ vectorDim: vector.length, topK, collection }, 'Qdrant search started');

    try {
      const points = await this.client.search(collection, {
        vector,
        limit: topK,
        score_threshold: minScore,
        with_payload: true,
      });

      const results: SearchResult[] = points.map((point) => ({
        id: String(point.id),
        similarity: point.score,
        payload: point.payload || {},
      }));

      logger.info({ resultCount: results.length, minScore, durationMs: Date.now() - startTime }, 'Qdrant search completed');
      return results;
    } catch (error) {
      const ragError = toRagError(SEARCH_FAILURE, error);
      logger.error({ err: error, durationMs: Date.now() - startTime }, ragError.message);
      throw ragError;
    }
  }
}
