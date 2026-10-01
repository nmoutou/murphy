import type { EmbeddingConfig } from '../config';
import type { EmbeddingVector, RagFailure } from '../types/rag';
import { logger as rootLogger } from '../utils/logger';
import { toRagError } from '../types/rag';

const logger = rootLogger.child({ context: 'embedding' });

interface TEIEmbeddingRequest {
  model: string;
  input: string[];
}

const EMBEDDING_FAILURE: RagFailure = { stage: 'embedding', code: 'NETWORK', operation: 'generate embeddings' };

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null;

const isNumberArray = (value: unknown): value is number[] =>
  Array.isArray(value) && value.every((component) => typeof component === 'number');

/**
 * Premier vecteur d'une réponse TEI `/v1/embeddings` (`{ data: [{ embedding }] }`)
 * @throws si le corps n'a pas cette forme
 */
const readEmbedding = (body: unknown): EmbeddingVector => {
  const entries = isRecord(body) ? body.data : undefined;
  const firstEntry: unknown = Array.isArray(entries) ? entries[0] : undefined;
  const embedding = isRecord(firstEntry) ? firstEntry.embedding : undefined;
  if (!isNumberArray(embedding)) throw new Error('Invalid embedding response format');
  return embedding;
};

export class EmbeddingClient {
  constructor(private readonly settings: EmbeddingConfig) {}

  /** @throws RagError d'étape `embedding` */
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
