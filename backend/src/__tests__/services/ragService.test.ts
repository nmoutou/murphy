/**
 * RAG Service Tests
 * Stage helpers of the pipeline: embedding, retrieval, passage fetch, context building
 */

import type { Passage, RetrievedChunk, StoredDocument } from '../../types/rag';
import {
  buildContextString,
  embedQuestion,
  fetchPassages,
  retrieveChunks,
} from '../../services/ragService';
import { getInfraClients } from '../../infra/clients';

jest.mock('../../infra/clients', () => {
  const clients = {
    embedding: { embedText: jest.fn() },
    qdrant: { searchVectors: jest.fn() },
    mongo: { fetchParentDocuments: jest.fn() },
    llm: { stream: jest.fn() },
  };
  return { getInfraClients: () => clients };
});
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

const EMBEDDING = [0.1, 0.2, 0.3];
const DOCUMENT: StoredDocument = {
  identifier: 'LEGIARTI000006419304',
  ownerId: 'default',
  title: 'Code civil, art. 2224',
  content: 'Article 2224. Cinq ans.',
};
const CHUNK: RetrievedChunk = {
  chunkId: 'LEGIARTI000006419304_0001',
  identifier: DOCUMENT.identifier,
  ownerId: DOCUMENT.ownerId,
  charStart: 14,
  charEnd: 23,
  score: 0.9,
};
const PASSAGE: Passage = { chunk: CHUNK, document: DOCUMENT, text: 'Cinq ans.', highlightStart: 14, highlightEnd: 23 };

const { embedding, qdrant, mongo } = getInfraClients();

describe('buildContextString', () => {
  it('says so when no document was found', () => {
    expect(buildContextString([])).toBe('No relevant documents found.');
  });

  it('numbers the passages and gives the passage alone, not its whole document', () => {
    const second: Passage = { ...PASSAGE, document: { ...DOCUMENT, title: 'Code civil, art. 2225' }, text: 'Dix ans.' };

    expect(buildContextString([PASSAGE, second])).toBe(
      '[1] Code civil, art. 2224\nCinq ans.\n\n[2] Code civil, art. 2225\nDix ans.',
    );
  });
});

describe('fetchPassages', () => {
  it('skips MongoDB when there is no chunk', async () => {
    await expect(fetchPassages([])).resolves.toEqual({ passages: [], docFetchMs: 0 });
    expect(mongo.fetchParentDocuments).not.toHaveBeenCalled();
  });

  it('reads the parents of the chunks and cuts the passages out', async () => {
    jest.mocked(mongo.fetchParentDocuments).mockResolvedValue([DOCUMENT]);

    const fetched = await fetchPassages([CHUNK]);

    expect(mongo.fetchParentDocuments).toHaveBeenCalledWith([CHUNK]);
    expect(fetched.passages).toEqual([PASSAGE]);
    expect(fetched.docFetchMs).toBeGreaterThanOrEqual(0);
  });

  it('refuses a chunk whose parent is missing', async () => {
    jest.mocked(mongo.fetchParentDocuments).mockResolvedValue([]);

    await expect(fetchPassages([CHUNK])).rejects.toMatchObject({ code: 'CONTRACT_VIOLATION' });
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
    jest.mocked(qdrant.searchVectors).mockResolvedValue([CHUNK]);

    const retrieved = await retrieveChunks(EMBEDDING, 3);

    expect(qdrant.searchVectors).toHaveBeenCalledWith(EMBEDDING, 3);
    expect(retrieved.chunks).toEqual([CHUNK]);
    expect(retrieved.retrievalMs).toBeGreaterThanOrEqual(0);
  });
});
