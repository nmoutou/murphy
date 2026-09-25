/**
 * TEI (Text Embeddings Inference) Client
 * Handles embedding generation with configurable timeout
 */

import type { EmbeddingConfig } from '../config';
import type { EmbeddingVector, RagFailure } from '../types/rag';
import { logger } from '../utils/logger';
import { toRagError } from '../types/rag';

interface TEIEmbeddingRequest {
  model: string;
  input: string[];
}

const EMBEDDING_FAILURE: RagFailure = { stage: 'embedding', code: 'NETWORK', operation: 'generate embeddings' };

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null;

const isNumberArray = (value: unknown): value is number[] =>
  Array.isArray(value) && value.every((component) => typeof component === 'number');

/**
 * First vector of a TEI `/v1/embeddings` response (`{ data: [{ embedding }] }`)
 * @throws Error when the body does not have that shape
 */
const readEmbedding = (body: unknown): EmbeddingVector => {
  const entries = isRecord(body) ? body.data : undefined;
  const firstEntry: unknown = Array.isArray(entries) ? entries[0] : undefined;
  const embedding = isRecord(firstEntry) ? firstEntry.embedding : undefined;
  if (!isNumberArray(embedding)) throw new Error('Invalid embedding response format');
  return embedding;
};

/**
 * Embedding client for TEI service
 */
export class EmbeddingClient {
  constructor(private readonly settings: EmbeddingConfig) {}

  /**
   * Embed a single text string
   * @param text Text to embed
   * @returns Embedding vector, sized by the configured model
   * @throws RagError with stage='embedding'
   */
  async embedText(text: string): Promise<EmbeddingVector> {
    const startTime = Date.now();
    logger.info({ textLength: text.length, modelName: this.settings.modelName }, 'Embedding request started');

    try {
      const embedding = await this.requestEmbedding(text);
      logger.info({ embeddingDim: embedding.length, durationMs: Date.now() - startTime }, 'Embedding completed');
      return embedding;
    } catch (error) {
      const ragError = toRagError(EMBEDDING_FAILURE, error);
      logger.error({ err: error, durationMs: Date.now() - startTime }, ragError.message);
      throw ragError;
    }
  }

  private async requestEmbedding(text: string): Promise<EmbeddingVector> {
    const response = await fetch(`${this.settings.serviceUrl}/v1/embeddings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: this.settings.modelName, input: [text] } satisfies TEIEmbeddingRequest),
      signal: AbortSignal.timeout(this.settings.timeoutMs),
    });

    if (!response.ok) {
      throw new Error(`TEI service returned ${response.status}: ${response.statusText}`);
    }

    const body: unknown = await response.json();
    return readEmbedding(body);
  }
}
