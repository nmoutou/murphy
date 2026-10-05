import { OpenSearchClient } from '../../infra/opensearch';

const mockClientConstructor = jest.fn();
const mockExists = jest.fn();
const mockPutPipeline = jest.fn();
const mockSearch = jest.fn();

// Une classe, pas un `jest.fn` : `restoreMocks` réinitialiserait son implémentation entre les tests
jest.mock('@opensearch-project/opensearch', () => ({
  Client: class {
    indices = { exists: mockExists };
    searchPipeline = { put: mockPutPipeline };
    search = mockSearch;

    constructor(options: unknown) {
      mockClientConstructor(options);
    }
  },
}));
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

const OPTIONS = {
  opensearch: { url: 'http://opensearch.test:9200', index: 'documents', timeoutMs: 2500 },
  pagination: { size: 10, depth: 100 },
};
const VECTOR = [0.1, 0.2, 0.3];
const QUESTION = 'affectations de recettes';
const SECTION_HIT = {
  _id: 'LEGISCTA000006114781',
  _source: { identifier: 'LEGISCTA000006114781', document_type: 'section', nature: null, passages: [] },
};

const timeoutError = (): Error => Object.assign(new Error('Request timed out'), { name: 'TimeoutError' });

beforeEach(() => {
  mockExists.mockResolvedValue({ body: true });
  mockPutPipeline.mockResolvedValue({ body: { acknowledged: true } });
  mockSearch.mockResolvedValue({ body: { hits: { hits: [SECTION_HIT] } } });
});

describe('OpenSearchClient', () => {
  it('gives the client its timeout, without retry', () => {
    new OpenSearchClient(OPTIONS);

    expect(mockClientConstructor).toHaveBeenCalledWith({ node: OPTIONS.opensearch.url, requestTimeout: 2500, maxRetries: 0 });
  });

  it('writes the RRF pipeline once the index is found', async () => {
    await new OpenSearchClient(OPTIONS).prepareSearch();

    expect(mockExists).toHaveBeenCalledWith({ index: 'documents' });
    expect(mockPutPipeline).toHaveBeenCalledWith({
      id: 'murphy-rrf',
      body: { phase_results_processors: [{ 'score-ranker-processor': { combination: { technique: 'rrf' } } }] },
    });
  });

  it('refuses to boot when the index does not exist, pointing to the ingestion', async () => {
    mockExists.mockResolvedValue({ body: false });

    await expect(new OpenSearchClient(OPTIONS).prepareSearch()).rejects.toThrow(
      'The OpenSearch index "documents" (OPENSEARCH_INDEX) does not exist. Run the ingestion: kedro run.',
    );
    expect(mockPutPipeline).not.toHaveBeenCalled();
  });

  it('refuses to boot when OpenSearch is unreachable, naming its URL', async () => {
    mockExists.mockRejectedValue(new Error('connect ECONNREFUSED'));

    await expect(new OpenSearchClient(OPTIONS).prepareSearch()).rejects.toThrow(
      'OpenSearch unreachable (http://opensearch.test:9200)',
    );
  });

  it('searches the index through the RRF pipeline, at the configured page size and depth', async () => {
    const hits = await new OpenSearchClient(OPTIONS).search(QUESTION, VECTOR);

    const [request] = mockSearch.mock.calls[0];
    expect(request).toMatchObject({
      index: 'documents',
      search_pipeline: 'murphy-rrf',
      body: { from: 0, size: 10, query: { hybrid: { pagination_depth: 100 } } },
    });
    expect(hits).toEqual([expect.objectContaining({ identifier: 'LEGISCTA000006114781', documentType: 'section' })]);
  });

  it.each([
    ['a failed search', new Error('connect ECONNREFUSED'), 'SEARCH_FAILED'],
    ['a timeout', timeoutError(), 'TIMEOUT'],
  ])('reports %s as a retrieval error', async (_case, error, code) => {
    mockSearch.mockRejectedValue(error);

    await expect(new OpenSearchClient(OPTIONS).search(QUESTION, VECTOR)).rejects.toMatchObject({ stage: 'retrieval', code });
  });

  it('reports an invalid document as a contract violation, not a failed search', async () => {
    mockSearch.mockResolvedValue({ body: { hits: { hits: [{ _id: 'X', _source: { identifier: 'X' } }] } } });

    await expect(new OpenSearchClient(OPTIONS).search(QUESTION, VECTOR)).rejects.toMatchObject({
      stage: 'retrieval',
      code: 'CONTRACT_VIOLATION',
    });
  });
});
