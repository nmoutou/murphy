/**
 * RAG Service
 * Helper functions for the Retrieval-Augmented Generation pipeline.
 */

import type { Document, SearchResult } from '../types/rag';
import { logger as rootLogger } from '../utils/logger';
import { getInfraClients } from '../infra/clients';

const logger = rootLogger.child({ context: 'ragService' });

export interface EmbedResult {
  embedding: number[];
  embeddingMs: number;
}

export interface RetrievalResult {
  results: SearchResult[];
  retrievalMs: number;
}

export interface DocFetchResult {
  documents: Document[];
  docFetchMs: number;
}

export async function embedQuestion(question: string): Promise<EmbedResult> {
  const start = Date.now();
  const embedding = await getInfraClients().embedding.embedText(question);
  return { embedding, embeddingMs: Date.now() - start };
}

export async function retrieveChunks(embedding: number[], topK: number): Promise<RetrievalResult> {
  const start = Date.now();
  const results = await getInfraClients().qdrant.searchVectors(embedding, topK);
  return { results, retrievalMs: Date.now() - start };
}

export async function fetchChunkDocuments(chunkIds: string[]): Promise<DocFetchResult> {
  if (chunkIds.length === 0) {
    logger.warn('No documents to fetch (empty chunkId list)');
    return { documents: [], docFetchMs: 0 };
  }
  const start = Date.now();
  const documents = await getInfraClients().mongo.fetchDocuments(chunkIds);
  return { documents, docFetchMs: Date.now() - start };
}

export function buildContextString(documents: Document[]): string {
  if (documents.length === 0) {
    return 'No relevant documents found.';
  }

  return documents
    .map((doc, idx) => {
      const title = doc.title ?? `Document ${idx + 1}`;
      const content = doc.content ?? '(No content available)';
      return `[${idx + 1}] ${title}\n${content}`;
    })
    .join('\n\n');
}
