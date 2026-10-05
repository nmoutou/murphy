import { closeInfraClients, getInfraClients, initInfraClients } from '../../infra/clients';
import { loadConfig } from '../../config';

const mockMongo = { close: jest.fn() };
const mockPrepareSearch = jest.fn();

jest.mock('../../infra/mongodb', () => ({ MongoDbClient: { connect: async () => mockMongo } }));
// Une classe, pas un `jest.fn` : `restoreMocks` réinitialiserait son implémentation entre les tests
jest.mock('../../infra/opensearch', () => ({
  OpenSearchClient: class {
    prepareSearch = mockPrepareSearch;
  },
}));
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

const { config } = loadConfig({ OPENSEARCH_URL: 'http://opensearch.test', OPENSEARCH_INDEX: 'documents' });

beforeEach(() => {
  mockPrepareSearch.mockResolvedValue(undefined);
});

afterEach(async () => {
  await closeInfraClients();
});

describe('infrastructure clients', () => {
  it('refuses access before the boot has created them', () => {
    expect(() => getInfraClients()).toThrow('Infrastructure clients not initialized');
  });

  it('shares the clients created at boot, once the search is prepared', async () => {
    await initInfraClients(config);

    expect(getInfraClients().mongo).toBe(mockMongo);
    expect(mockPrepareSearch).toHaveBeenCalled();
  });

  it('refuses to boot when the search cannot be prepared', async () => {
    mockPrepareSearch.mockRejectedValue(new Error('The OpenSearch index "documents" (OPENSEARCH_INDEX) does not exist'));

    await expect(initInfraClients(config)).rejects.toThrow('The OpenSearch index "documents"');
    expect(() => getInfraClients()).toThrow('Infrastructure clients not initialized');
  });

  it('closes MongoDB at shutdown, then refuses access again', async () => {
    await initInfraClients(config);

    await closeInfraClients();

    expect(mockMongo.close).toHaveBeenCalled();
    expect(() => getInfraClients()).toThrow('Infrastructure clients not initialized');
  });

  it('does nothing when closing clients that were never created', async () => {
    await expect(closeInfraClients()).resolves.toBeUndefined();
  });
});
