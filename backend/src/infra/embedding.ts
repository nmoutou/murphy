/**
 * TEI (Text Embeddings Inference) Client
 * Handles embedding generation with configurable timeout
 */

import { logger } from '../utils/logger';
import { RagError, EmbeddingVector } from '../types/rag';

interface TEIEmbeddingRequest {
  model: string;
  input: string[];
}

interface TEIEmbeddingResponse {
  data: Array<{
    embedding: number[];
    index: number;
  }>;
}

/**
 * Embedding client for TEI service
 */
export class EmbeddingClient {
  private readonly serviceUrl: string;
  private readonly modelName: string;
  private readonly timeoutMs: number;

  constructor(
    serviceUrl: string = process.env.EMBEDDING_SERVICE_URL || 'http://embedding-service:80',
    modelName: string = process.env.EMBEDDING_MODEL_NAME || 'all-mpnet-base-v2',
    timeoutMs: number = parseInt(process.env.EMBEDDING_SERVICE_TIMEOUT || '10000', 10)
  ) {
    this.serviceUrl = serviceUrl;
    this.modelName = modelName;
    this.timeoutMs = timeoutMs;
  }

  /**
   * Embed a single text string
   * @param text Text to embed
   * @returns 768-dimensional embedding vector
   * @throws RagError with stage='embedding'
   */
  async embedText(text: string): Promise<EmbeddingVector> {
    const startTime = Date.now();

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);

      try {
        logger.info(
          { textLength: text.length, modelName: this.modelName },
          'Embedding request started'
        );

        const response = await fetch(`${this.serviceUrl}/v1/embeddings`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model: this.modelName,
            input: [text],
          } as TEIEmbeddingRequest),
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(
            `TEI service returned ${response.status}: ${response.statusText}`
          );
        }

        const data = (await response.json()) as TEIEmbeddingResponse;

        if (!data.data || !data.data[0] || !data.data[0].embedding) {
          throw new Error('Invalid embedding response format');
        }

        const embedding = data.data[0].embedding;
        const duration = Date.now() - startTime;

        logger.info(
          { embeddingDim: embedding.length, durationMs: duration },
          'Embedding completed'
        );

        return embedding;
      } finally {
        clearTimeout(timeoutId);
      }
    } catch (error) {
      const duration = Date.now() - startTime;
      const errorMessage = error instanceof Error ? error.message : String(error);

      logger.error(
        { errorMessage, errorType: error instanceof Error ? error.name : undefined, durationMs: duration },
        'Embedding failed'
      );

      throw new RagError(
        'embedding',
        errorMessage.includes('abort') ? 'TIMEOUT' : 'NETWORK',
        `Failed to generate embeddings: ${errorMessage}`,
      );
    }
  }
}
