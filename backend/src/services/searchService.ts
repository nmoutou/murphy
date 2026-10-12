import type { Passage as ContractPassage, SearchResponse, SearchResult } from '@murphy/contract/search';
import type { FoundDocument, Passage, ResultWindow } from '../types/rag';
import type { PagedSearchRequest } from '../validation/searchRequest';
import { logger as rootLogger } from '../utils/logger';
import { config } from '../config';
import { RagError } from '../types/rag';
import { embedQuestion, retrieveDocuments, fetchDocuments } from './ragService';

const logger = rootLogger.child({ context: 'searchService' });

/** L'`ETAT` de la DILA d'un texte en vigueur ; `VIGUEUR_DIFF` (à venir) ne l'est pas encore */
const IN_FORCE_STATUS = 'VIGUEUR';

export interface PageWindow extends ResultWindow {
  readonly pageCount: number;
}

/**
 * Arrondi par excès, dernière page tronquée : `from + size` ne dépasse jamais la
 * profondeur, et aucun document classé n'est perdu
 */
export const toPageWindow = (page: number, pageSize: number, depth: number): PageWindow => {
  const from = (page - 1) * pageSize;
  return { from, size: Math.min(pageSize, depth - from), pageCount: Math.ceil(depth / pageSize) };
};

const toInForce = (status: string | undefined): boolean | undefined =>
  status === undefined ? undefined : status === IN_FORCE_STATUS;

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
  isInForce: toInForce(document.status),
  contentLength: document.contentLength,
  passages: passages.map(toContractPassage),
});

/**
 * Une page de documents classés et de leurs passages correspondants
 * @throws RagError `PAGE_OUT_OF_RANGE` au-delà de la dernière page, ou celle de l'étape en échec
 */
export const searchDocuments = async ({ question, page, pageSize }: PagedSearchRequest): Promise<SearchResponse> => {
  const { pageCount, ...window } = toPageWindow(page, pageSize, config.pagination.depth);
  if (page > pageCount) {
    throw new RagError('request', 'PAGE_OUT_OF_RANGE', `Page ${page} is beyond the last page, ${pageCount}`);
  }
  const startTime = Date.now();

  const { embedding, embeddingMs } = await embedQuestion(question);
  const { documents: retrieved, retrievalMs } = await retrieveDocuments(question, embedding, window);
  const { documents, docFetchMs } = await fetchDocuments(retrieved);

  const timing = { embeddingMs, retrievalMs, docFetchMs, totalMs: Date.now() - startTime };
  logger.info(
    { questionLength: question.length, page, pageSize, resultCount: documents.length, ...timing },
    'Search completed',
  );
  const results = documents.map(toSearchResult);
  const pageSizes = [...config.pagination.sizes];
  return { page, pageCount, pageSize, pageSizes, contextBudget: config.llm.contextMaxChars, results };
};
