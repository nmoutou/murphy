/**
 * Qdrant Client Tests
 * The search call and the projection of its points, over a mocked Qdrant client
 */

import { QdrantVectorClient } from '../../infra/qdrant';

const mockSearch = jest.fn();

// A class, not a `jest.fn`: `restoreMocks` would reset its implementation between tests
jest.mock('@qdrant/qdrant-js', () => ({
  QdrantClient: class {
    search = mockSearch;
  },
}));
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

const OPTIONS = { url: 'http://qdrant.test', collection: 'collection-test', minScore: 0.5 };
const VECTOR = [0.1, 0.2, 0.3];
const TOP_K = 3;

describe('QdrantVectorClient.searchVectors', () => {
  it('searches the configured collection and projects the points', async () => {
    mockSearch.mockResolvedValue([
      { id: 7, score: 0.9, payload: { chunkId: 'chunk-1' } },
      { id: 'point-2', score: 0.6, payload: null },
    ]);

    await expect(new QdrantVectorClient(OPTIONS).searchVectors(VECTOR, TOP_K)).resolves.toEqual([
      { id: '7', similarity: 0.9, payload: { chunkId: 'chunk-1' } },
      { id: 'point-2', similarity: 0.6, payload: {} },
    ]);
    expect(mockSearch).toHaveBeenCalledWith('collection-test', {
      vector: VECTOR,
      limit: TOP_K,
      score_threshold: 0.5,
      with_payload: true,
    });
  });

  it('fails with a retrieval RagError when the search fails', async () => {
    mockSearch.mockRejectedValue(new Error('Bad Request'));

    await expect(new QdrantVectorClient(OPTIONS).searchVectors(VECTOR, TOP_K)).rejects.toMatchObject({
      stage: 'retrieval',
      code: 'SEARCH_FAILED',
      message: 'Failed to search Qdrant: Bad Request',
    });
  });

  it('reports a client timeout as such', async () => {
    mockSearch.mockRejectedValue(Object.assign(new Error('Request timed out'), { name: 'QdrantClientTimeoutError' }));

    await expect(new QdrantVectorClient(OPTIONS).searchVectors(VECTOR, TOP_K)).rejects.toMatchObject({ code: 'TIMEOUT' });
  });
});
