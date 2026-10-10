import type { Passage as ContractPassage, SearchRequest, SearchResponse, SearchResult } from '@murphy/contract/search';
import type { FoundDocument, Passage } from '../types/rag';
import { logger as rootLogger } from '../utils/logger';
import { config } from '../config';
import { RagError } from '../types/rag';
import { embedQuestion, retrieveDocuments, fetchDocuments } from './ragService';

const logger = rootLogger.child({ context: 'searchService' });

/** Arrondi par défaut : `from + size` ne dépasse jamais la profondeur (ADR-031 §2) */
export const PAGE_COUNT = Math.floor(config.pagination.depth / config.pagination.size);

const toContractPassage = ({ ref, text, highlightStart, highlightEnd }: Passage): ContractPassage => ({
  chunkId: ref.chunkId,
  text,
  start: highlightStart,
  end: highlightEnd,
});

const toSearchResult = ({ document, documentType, nature, passages }: FoundDocument): SearchResult => ({
  identifier: document.identifier,
  title: document.title,
  documentType,
  nature,
  passages: passages.map(toContractPassage),
});

/**
 * Une page de documents classés et de leurs passages correspondants
 * @throws RagError `PAGE_OUT_OF_RANGE` au-delà de `PAGE_COUNT`, ou celle de l'étape en échec
 */
export const searchDocuments = async ({ question, page }: SearchRequest): Promise<SearchResponse> => {
  if (page > PAGE_COUNT) {
    throw new RagError('request', 'PAGE_OUT_OF_RANGE', `Page ${page} is beyond the last page, ${PAGE_COUNT}`);
  }
  const startTime = Date.now();
  const from = (page - 1) * config.pagination.size;

  const { embedding, embeddingMs } = await embedQuestion(question);
  const { documents: retrieved, retrievalMs } = await retrieveDocuments(question, embedding, from);
  const { documents, docFetchMs } = await fetchDocuments(retrieved);

  const timing = { embeddingMs, retrievalMs, docFetchMs, totalMs: Date.now() - startTime };
  logger.info({ questionLength: question.length, page, resultCount: documents.length, ...timing }, 'Search completed');
  return { page, pageCount: PAGE_COUNT, results: documents.map(toSearchResult) };
};
