/**
 * RAG Service Tests
 * Stage helpers of the pipeline: embedding, retrieval, document fetch, context building
 */

import {
  buildContextString,
  embedQuestion,
  fetchChunkDocuments,
  retrieveChunks,
} from '../../services/ragService';
import { getInfraClients } from '../../infra/clients';

jest.mock('../../infra/clients', () => {
  const clients = {
    embedding: { embedText: jest.fn() },
    qdrant: { searchVectors: jest.fn() },
    mongo: { fetchDocuments: jest.fn() },
    llm: { stream: jest.fn() },
  };
  return { getInfraClients: () => clients };
});
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

const EMBEDDING = [0.1, 0.2, 0.3];

const { embedding, qdrant, mongo } = getInfraClients();

describe('buildContextString', () => {
  it('says so when no document was found', () => {
    expect(buildContextString([])).toBe('No relevant documents found.');
  });

  it('numbers the documents and falls back on missing title or content', () => {
    const context = buildContextString([
      { chunkId: 'chunk-1', title: 'Code civil, art. 2224', content: 'Cinq ans.' },
      { chunkId: 'chunk-2' },
    ]);

    expect(context).toBe('[1] Code civil, art. 2224\nCinq ans.\n\n[2] Document 2\n(No content available)');
  });
});

describe('fetchChunkDocuments', () => {
  it('skips MongoDB when there is no chunk to fetch', async () => {
    await expect(fetchChunkDocuments([])).resolves.toEqual({ documents: [], docFetchMs: 0 });
    expect(mongo.fetchDocuments).not.toHaveBeenCalled();
  });

  it('returns the fetched documents with the stage duration', async () => {
    const documents = [{ chunkId: 'chunk-1', content: 'Cinq ans.' }];
    jest.mocked(mongo.fetchDocuments).mockResolvedValue(documents);

    const fetched = await fetchChunkDocuments(['chunk-1']);

    expect(mongo.fetchDocuments).toHaveBeenCalledWith(['chunk-1']);
    expect(fetched.documents).toBe(documents);
    expect(fetched.docFetchMs).toBeGreaterThanOrEqual(0);
  });
});

describe('embedQuestion', () => {
  it('returns the embedding with the stage duration', async () => {
    jest.mocked(embedding.embedText).mockResolvedValue(EMBEDDING);

    const embedded = await embedQuestion('Quel délai ?');

    expect(embedding.embedText).toHaveBeenCalledWith('Quel délai ?');
    expect(embedded.embedding).toBe(EMBEDDING);
    expect(embedded.embeddingMs).toBeGreaterThanOrEqual(0);
  });
});

describe('retrieveChunks', () => {
  it('searches the requested number of chunks', async () => {
    const results = [{ id: '1', similarity: 0.9, payload: { chunkId: 'chunk-1' } }];
    jest.mocked(qdrant.searchVectors).mockResolvedValue(results);

    const retrieved = await retrieveChunks(EMBEDDING, 3);

    expect(qdrant.searchVectors).toHaveBeenCalledWith(EMBEDDING, 3);
    expect(retrieved.results).toBe(results);
    expect(retrieved.retrievalMs).toBeGreaterThanOrEqual(0);
  });
});
