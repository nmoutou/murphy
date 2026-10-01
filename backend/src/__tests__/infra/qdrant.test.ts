import { QdrantVectorClient } from '../../infra/qdrant';

const mockSearch = jest.fn();
const mockCollectionExists = jest.fn();
const mockQdrantClientConstructor = jest.fn();

// Une classe, pas un `jest.fn` : `restoreMocks` réinitialiserait son implémentation entre les tests
jest.mock('@qdrant/qdrant-js', () => ({
  QdrantClient: class {
    search = mockSearch;
    collectionExists = mockCollectionExists;

    constructor(args: unknown) {
      mockQdrantClientConstructor(args);
    }
  },
}));
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

const OPTIONS = { url: 'http://qdrant.test', timeoutMs: 2500, collection: 'collection-test', minScore: 0.5 };
const VECTOR = [0.1, 0.2, 0.3];
const TOP_K = 3;
/** `nature` est facultatif dans le contrat, `document_type` non */
const CONTRACT_PAYLOAD = {
  chunk_id: 'LEGITEXT000006069577_0001',
  identifier: 'LEGITEXT000006069577',
  char_start: 0,
  char_end: 42,
  document_type: 'texte',
  nature: 'LOI',
  num: 'L2122-22',
};

describe('QdrantVectorClient', () => {
  it('gives the Qdrant client its timeout, in milliseconds', () => {
    new QdrantVectorClient(OPTIONS);

    expect(mockQdrantClientConstructor).toHaveBeenCalledWith({ url: 'http://qdrant.test', timeout: 2500 });
  });
});

describe('QdrantVectorClient.assertCollectionExists', () => {
  it('accepts a collection that exists', async () => {
    mockCollectionExists.mockResolvedValue({ exists: true });

    await expect(new QdrantVectorClient(OPTIONS).assertCollectionExists()).resolves.toBeUndefined();
    expect(mockCollectionExists).toHaveBeenCalledWith('collection-test');
  });

  it('refuses a collection that does not exist, naming it', async () => {
    mockCollectionExists.mockResolvedValue({ exists: false });

    await expect(new QdrantVectorClient(OPTIONS).assertCollectionExists()).rejects.toThrow(
      'The Qdrant collection "collection-test" (QDRANT_COLLECTION) does not exist'
    );
  });

  it('reports an unreachable Qdrant', async () => {
    mockCollectionExists.mockRejectedValue(new Error('connect ECONNREFUSED'));

    await expect(new QdrantVectorClient(OPTIONS).assertCollectionExists()).rejects.toThrow('Qdrant unreachable');
  });
});

describe('QdrantVectorClient.searchVectors', () => {
  it('searches the configured collection and reads the contract fields of each point', async () => {
    mockSearch.mockResolvedValue([
      { id: 7, score: 0.9, payload: CONTRACT_PAYLOAD },
      { id: 'point-2', score: 0.6, payload: { ...CONTRACT_PAYLOAD, chunk_id: 'chunk-2', nature: null } },
    ]);

    await expect(new QdrantVectorClient(OPTIONS).searchVectors(VECTOR, TOP_K)).resolves.toEqual([
      {
        chunkId: 'LEGITEXT000006069577_0001',
        identifier: 'LEGITEXT000006069577',
        charStart: 0,
        charEnd: 42,
        score: 0.9,
        documentType: 'texte',
        nature: 'LOI',
      },
      expect.objectContaining({ chunkId: 'chunk-2', nature: undefined }),
    ]);
    expect(mockSearch).toHaveBeenCalledWith('collection-test', {
      vector: VECTOR,
      limit: TOP_K,
      score_threshold: 0.5,
      with_payload: true,
    });
  });

  it.each([
    ['without offsets', { chunk_id: 'chunk-1', identifier: 'LEGIARTI1' }, 'chunk-1'],
    ['in the pre-contract format', { chunkId: 'chunk-1', title: 'Code civil' }, '7'],
    ['with a fractional offset', { ...CONTRACT_PAYLOAD, char_end: 4.5 }, CONTRACT_PAYLOAD.chunk_id],
    ['without document_type', { ...CONTRACT_PAYLOAD, document_type: undefined }, CONTRACT_PAYLOAD.chunk_id],
    ['in the pre-typing format', { ...CONTRACT_PAYLOAD, document_type: undefined, type_document: 'LOI' }, CONTRACT_PAYLOAD.chunk_id],
    ['with an unknown document_type', { ...CONTRACT_PAYLOAD, document_type: 'arret' }, CONTRACT_PAYLOAD.chunk_id],
    ['without payload', null, '7'],
  ])('reports a point %s as a contract violation, not as a failed search', async (_case, payload, pointName) => {
    mockSearch.mockResolvedValue([{ id: 7, score: 0.9, payload }]);

    const search = new QdrantVectorClient(OPTIONS).searchVectors(VECTOR, TOP_K);

    await expect(search).rejects.toMatchObject({ stage: 'retrieval', code: 'CONTRACT_VIOLATION' });
    await expect(search).rejects.toThrow(`Qdrant point ${pointName} lacks`);
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
