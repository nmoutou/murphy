/**
 * RAG Service Tests
 * Stage helpers of the pipeline: embedding, retrieval, document fetch, prompt building
 */

import {
  buildContextString,
  embedQuestion,
  fetchChunkDocuments,
  getDefaultSystemPrompt,
  retrieveChunks,
} from '../../services/ragService';
import { embeddingClient, qdrantClient } from '../../infra';
import { fetchDocuments } from '../../infra/mongodb';

jest.mock('../../infra', () => ({
  embeddingClient: { embedText: jest.fn() },
  qdrantClient: { searchVectors: jest.fn() },
}));
jest.mock('../../infra/mongodb', () => ({ fetchDocuments: jest.fn() }));
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

const EMBEDDING = [0.1, 0.2, 0.3];

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

describe('getDefaultSystemPrompt', () => {
  const initialPrompt = process.env.SYSTEM_PROMPT;

  afterEach(() => {
    if (initialPrompt === undefined) delete process.env.SYSTEM_PROMPT;
    else process.env.SYSTEM_PROMPT = initialPrompt;
  });

  it('defaults to the French legal-assistant prompt', () => {
    delete process.env.SYSTEM_PROMPT;

    expect(getDefaultSystemPrompt()).toContain('assistant juridique');
  });

  it('is overridden by SYSTEM_PROMPT', () => {
    process.env.SYSTEM_PROMPT = 'Consigne de test';

    expect(getDefaultSystemPrompt()).toBe('Consigne de test');
  });
});

describe('fetchChunkDocuments', () => {
  it('skips MongoDB when there is no chunk to fetch', async () => {
    await expect(fetchChunkDocuments([])).resolves.toEqual({ documents: [], docFetchMs: 0 });
    expect(fetchDocuments).not.toHaveBeenCalled();
  });

  it('returns the fetched documents with the stage duration', async () => {
    const documents = [{ chunkId: 'chunk-1', content: 'Cinq ans.' }];
    jest.mocked(fetchDocuments).mockResolvedValue(documents);

    const fetched = await fetchChunkDocuments(['chunk-1']);

    expect(fetchDocuments).toHaveBeenCalledWith(['chunk-1']);
    expect(fetched.documents).toBe(documents);
    expect(fetched.docFetchMs).toBeGreaterThanOrEqual(0);
  });
});

describe('embedQuestion', () => {
  it('returns the embedding with the stage duration', async () => {
    jest.mocked(embeddingClient.embedText).mockResolvedValue(EMBEDDING);

    const embedded = await embedQuestion('Quel délai ?');

    expect(embeddingClient.embedText).toHaveBeenCalledWith('Quel délai ?');
    expect(embedded.embedding).toBe(EMBEDDING);
    expect(embedded.embeddingMs).toBeGreaterThanOrEqual(0);
  });
});

describe('retrieveChunks', () => {
  it('searches the requested number of chunks', async () => {
    const results = [{ id: '1', similarity: 0.9, payload: { chunkId: 'chunk-1' } }];
    jest.mocked(qdrantClient.searchVectors).mockResolvedValue(results);

    const retrieved = await retrieveChunks(EMBEDDING, 3);

    expect(qdrantClient.searchVectors).toHaveBeenCalledWith(EMBEDDING, 3);
    expect(retrieved.results).toBe(results);
    expect(retrieved.retrievalMs).toBeGreaterThanOrEqual(0);
  });
});
