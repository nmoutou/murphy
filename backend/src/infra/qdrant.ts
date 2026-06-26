/**
 * Qdrant Vector Database Client
 * Handles semantic search with configurable timeout
 */

import { QdrantClient } from '@qdrant/qdrant-js';
import { logger } from '../utils/logger';
import { RagError, SearchResult, EmbeddingVector } from '../types/rag';

/**
 * Qdrant client for vector similarity search
 */
export class QdrantVectorClient {
  private readonly client: QdrantClient;
  private readonly collectionName: string;
  private readonly minScore: number;

  constructor(
    qdrantUrl: string = process.env.QDRANT_URL || 'http://qdrant:6333',
    collectionName: string = process.env.QDRANT_COLLECTION || 'chunks',
    minScore: number = parseFloat(process.env.RETRIEVAL_MIN_SCORE || '0.5')
  ) {
    this.client = new QdrantClient({
      url: qdrantUrl,
    });
    this.collectionName = collectionName;
    this.minScore = minScore;
  }

  /**
   * Search for similar vectors
   * @param vector Embedding vector (768 dimensions)
   * @param topK Number of results to return (default: 10)
   * @returns Array of search results ranked by similarity
   * @throws RagError with stage='retrieval'
   */
  async searchVectors(vector: EmbeddingVector, topK: number = 10): Promise<SearchResult[]> {
    const startTime = Date.now();

    try {
      logger.info(
        { vectorDim: vector.length, topK, collection: this.collectionName },
        'Qdrant search started'
      );

      const response = await this.client.search(this.collectionName, {
        vector: vector,
        limit: topK,
        score_threshold: this.minScore,
        with_payload: true,
      });

      const results: SearchResult[] = response.map((point: any) => ({
        id: String(point.id),
        similarity: point.score,
        payload: point.payload || {},
      }));

      const duration = Date.now() - startTime;

      logger.info(
        { resultCount: results.length, minScore: this.minScore, durationMs: duration },
        'Qdrant search completed'
      );

      return results;
    } catch (error) {
      const duration = Date.now() - startTime;
      const errorMessage = error instanceof Error ? error.message : String(error);

      logger.error(
        { errorMessage, errorType: (error as any)?.name, durationMs: duration },
        'Qdrant search failed'
      );

      throw new RagError(
        'retrieval',
        errorMessage.includes('timeout') || errorMessage.includes('Timeout') ? 'TIMEOUT' : 'SEARCH_FAILED',
        `Failed to search Qdrant: ${errorMessage}`,
      );
    }
  }


}
