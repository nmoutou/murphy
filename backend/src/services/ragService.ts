/**
 * RAG Service
 * Helper functions for the Retrieval-Augmented Generation pipeline.
 */

import { logger as rootLogger } from '../utils/logger';
import { fetchDocuments } from '../infra/mongodb';
import { embeddingClient, qdrantClient } from '../infra';
import { RagError, Document, SearchResult } from '../types/rag';

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
  const embedding = await embeddingClient.embedText(question);
  return { embedding, embeddingMs: Date.now() - start };
}

export async function retrieveChunks(embedding: number[], topK: number): Promise<RetrievalResult> {
  const start = Date.now();
  const results = await qdrantClient.searchVectors(embedding, topK);
  return { results, retrievalMs: Date.now() - start };
}

export async function fetchChunkDocuments(chunkIds: string[]): Promise<DocFetchResult> {
  if (chunkIds.length === 0) {
    logger.warn('No documents to fetch (empty chunkId list)');
    return { documents: [], docFetchMs: 0 };
  }
  const start = Date.now();
  const documents = await fetchDocuments(chunkIds);
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

export function getDefaultSystemPrompt(): string {
  return (
    process.env.SYSTEM_PROMPT ||
    'Vous êtes un assistant juridique intelligent spécialisé dans le droit français. ' +
    'Répondez aux questions de l\'utilisateur en vous basant sur les documents juridiques fournis. ' +
    'Soyez précis, professionnel et citez les sources pertinentes. ' +
    'Si la réponse ne se trouve pas dans les documents fournis, dites-le clairement.'
  );
}

export { RagError };

