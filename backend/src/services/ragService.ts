import type { Passage, RetrievedChunk } from '../types/rag';
import { logger as rootLogger } from '../utils/logger';
import { getInfraClients } from '../infra/clients';
import { assemblePassages } from './passages';

const logger = rootLogger.child({ context: 'ragService' });

/** Remplace les passages dans le prompt système quand la recherche n'en trouve aucun */
const NO_PASSAGE_CONTEXT = 'Aucun document pertinent trouvé.';

export interface EmbedResult {
  embedding: number[];
  embeddingMs: number;
}

export interface RetrievalResult {
  chunks: RetrievedChunk[];
  retrievalMs: number;
}

export interface PassageFetchResult {
  passages: Passage[];
  docFetchMs: number;
}

export const embedQuestion = async (question: string): Promise<EmbedResult> => {
  const start = Date.now();
  const embedding = await getInfraClients().embedding.embedText(question);
  return { embedding, embeddingMs: Date.now() - start };
};

export const retrieveChunks = async (embedding: number[], topK: number): Promise<RetrievalResult> => {
  const start = Date.now();
  const chunks = await getInfraClients().qdrant.searchVectors(embedding, topK);
  return { chunks, retrievalMs: Date.now() - start };
};

/**
 * @throws RagError d'étape `retrieval`, `CONTRACT_VIOLATION` si un parent ou ses offsets ne collent pas
 */
export const fetchPassages = async (chunks: readonly RetrievedChunk[]): Promise<PassageFetchResult> => {
  if (chunks.length === 0) {
    logger.warn('No passage to fetch: the search found no chunk');
    return { passages: [], docFetchMs: 0 };
  }
  const start = Date.now();
  const documents = await getInfraClients().mongo.fetchParentDocuments(chunks.map((chunk) => chunk.identifier));
  return { passages: assemblePassages(chunks, documents), docFetchMs: Date.now() - start };
};

/** Le LLM lit le passage seul, pas son document entier (ADR-015) */
export const buildContextString = (passages: readonly Passage[]): string => {
  if (passages.length === 0) {
    return NO_PASSAGE_CONTEXT;
  }

  return passages.map((passage, idx) => `[${idx + 1}] ${passage.document.title}\n${passage.text}`).join('\n\n');
};
