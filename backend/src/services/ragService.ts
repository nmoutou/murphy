import type { EmbeddingVector, FoundDocument, ResultWindow, RetrievedDocument } from '../types/rag';
import { logger as rootLogger } from '../utils/logger';
import { getInfraClients } from '../infra/clients';
import { assembleDocuments } from './passages';
import { toRetrievedDocument } from './passageRanking';

const logger = rootLogger.child({ context: 'ragService' });

export interface EmbedResult {
  embedding: EmbeddingVector;
  embeddingMs: number;
}

export interface RetrievalResult {
  documents: RetrievedDocument[];
  retrievalMs: number;
}

export interface DocumentFetchResult {
  documents: FoundDocument[];
  docFetchMs: number;
}

export const embedQuestion = async (question: string): Promise<EmbedResult> => {
  const start = Date.now();
  const embedding = await getInfraClients().embedding.embedQuestion(question);
  return { embedding, embeddingMs: Date.now() - start };
};

export const retrieveDocuments = async (
  question: string,
  embedding: EmbeddingVector,
  window: ResultWindow,
): Promise<RetrievalResult> => {
  const start = Date.now();
  const hits = await getInfraClients().opensearch.search(question, embedding, window);
  return { documents: hits.map(toRetrievedDocument), retrievalMs: Date.now() - start };
};

/**
 * @throws RagError d'étape `retrieval`, `CONTRACT_VIOLATION` si un document ou des offsets ne collent pas
 */
export const fetchDocuments = async (retrieved: readonly RetrievedDocument[]): Promise<DocumentFetchResult> => {
  if (retrieved.length === 0) {
    logger.warn('No document to fetch: the search found none');
    return { documents: [], docFetchMs: 0 };
  }
  const start = Date.now();
  const stored = await getInfraClients().mongo.fetchParentDocuments(retrieved.map(({ identifier }) => identifier));
  return { documents: assembleDocuments(retrieved, stored), docFetchMs: Date.now() - start };
};
