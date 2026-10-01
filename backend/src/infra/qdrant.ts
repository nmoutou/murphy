import { QdrantClient } from '@qdrant/qdrant-js';
import { documentTypeSchema, type DocumentType } from '@murphy/contract/messages';
import type { QdrantConfig } from '../config';
import type { EmbeddingVector, RagFailure, RetrievedChunk } from '../types/rag';
import { logger as rootLogger } from '../utils/logger';
import { contractViolation, toRagError } from '../types/rag';

const logger = rootLogger.child({ context: 'qdrant' });

export interface QdrantVectorClientOptions extends QdrantConfig {
  readonly minScore: number;
}

const INGESTION_COMMAND = 'kedro run';

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

const readDocumentType = (payload: Payload): DocumentType | undefined => {
  const parsed = documentTypeSchema.safeParse(payload?.document_type);
  return parsed.success ? parsed.data : undefined;
};

/**
 * Vérifie le payload d'un point contre le contrat de service (ADR-039)
 * @throws RagError `CONTRACT_VIOLATION` nommant le point si un champ manque
 */
export const toRetrievedChunk = ({ id, score, payload }: ScoredPoint): RetrievedChunk => {
  const chunkId = readString(payload, 'chunk_id');
  const identifier = readString(payload, 'identifier');
  const charStart = readInteger(payload, 'char_start');
  const charEnd = readInteger(payload, 'char_end');
  const documentType = readDocumentType(payload);
  if (!chunkId || !identifier || charStart === undefined || charEnd === undefined || !documentType) {
    throw contractViolation(
      `Qdrant point ${chunkId ?? String(id)} lacks chunk_id, identifier, char_start, char_end or a known document_type`
    );
  }
  return { chunkId, identifier, charStart, charEnd, score, documentType, nature: readString(payload, 'nature') };
};

export class QdrantVectorClient {
  private readonly client: QdrantClient;

  constructor(private readonly options: QdrantVectorClientOptions) {
    this.client = new QdrantClient({ url: options.url, timeout: options.timeoutMs });
  }

  /** @throws si Qdrant est injoignable ou la collection absente */
  async assertCollectionExists(): Promise<void> {
    const { url, collection } = this.options;
    const { exists } = await this.client.collectionExists(collection).catch((error) => {
      throw new Error(`Qdrant unreachable (${url}): cannot check the collection "${collection}". Cause: ${String(error)}`);
    });
    if (!exists) {
      throw new Error(
        `The Qdrant collection "${collection}" (QDRANT_COLLECTION) does not exist. Run the ingestion: ${INGESTION_COMMAND}.`
      );
    }
    logger.info({ collection }, 'Qdrant collection found');
  }

  /** @throws RagError d'étape `retrieval`, ou `CONTRACT_VIOLATION` sur un payload invalide */
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

    // Hors du `try` : une violation de contrat n'est pas une recherche échouée
    const chunks = points.map(toRetrievedChunk);
    logger.info({ resultCount: chunks.length, minScore, durationMs: Date.now() - startTime }, 'Qdrant search completed');
    return chunks;
  }
}
