import type { EmbeddingVector, FoundDocument, RetrievedDocument } from '../types/rag';
import { logger as rootLogger } from '../utils/logger';
import { getInfraClients } from '../infra/clients';
import { assembleDocuments } from './passages';
import { toRetrievedDocument } from './passageRanking';

const logger = rootLogger.child({ context: 'ragService' });

/** Remplace les passages dans le prompt système quand la recherche n'en trouve aucun */
const NO_PASSAGE_CONTEXT = 'Aucun document pertinent trouvé.';
/**
 * Un document trouvé par ses métadonnées envoie tous ses passages : une décision entière
 * dépasse 140 000 caractères (ADR-028, étape 1)
 */
export const MAX_LLM_CONTEXT_CHARS = 200_000;
const CONTEXT_SEPARATOR = '\n\n';

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
  const embedding = await getInfraClients().embedding.embedText(question);
  return { embedding, embeddingMs: Date.now() - start };
};

export const retrieveDocuments = async (question: string, embedding: EmbeddingVector): Promise<RetrievalResult> => {
  const start = Date.now();
  const hits = await getInfraClients().opensearch.search(question, embedding);
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

/**
 * Le LLM lit les passages seuls, pas leurs documents (ADR-015), dans l'ordre du classement,
 * jusqu'à `MAX_LLM_CONTEXT_CHARS` : le passage qui ferait dépasser arrête le remplissage
 */
export const buildContextString = (documents: readonly FoundDocument[]): string => {
  const passages = documents.flatMap(({ document, passages: found }) =>
    found.map(({ text }) => ({ title: document.title, text }))
  );
  if (passages.length === 0) return NO_PASSAGE_CONTEXT;

  const blocks: string[] = [];
  let length = 0;
  for (const { title, text } of passages) {
    const block = `[${blocks.length + 1}] ${title}\n${text}`;
    const nextLength = length + (blocks.length > 0 ? CONTEXT_SEPARATOR.length : 0) + block.length;
    if (nextLength > MAX_LLM_CONTEXT_CHARS) break;
    blocks.push(block);
    length = nextLength;
  }
  if (blocks.length < passages.length) {
    logger.warn(
      { kept: blocks.length, dropped: passages.length - blocks.length, maxChars: MAX_LLM_CONTEXT_CHARS },
      'LLM context capped: the lowest-ranked passages are left out'
    );
  }
  return blocks.join(CONTEXT_SEPARATOR);
};
