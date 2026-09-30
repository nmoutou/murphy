/**
 * Infrastructure Clients Tests
 * Creation at boot, access, and shutdown of the shared clients
 */

import { closeInfraClients, getInfraClients, initInfraClients } from '../../infra/clients';
import { loadConfig } from '../../config';

const mockMongo = { close: jest.fn() };
const mockCollectionExists = jest.fn();

jest.mock('../../infra/mongodb', () => ({ MongoDbClient: { connect: async () => mockMongo } }));
// A class, not a `jest.fn`: `restoreMocks` would reset its implementation between tests
jest.mock('@qdrant/qdrant-js', () => ({
  QdrantClient: class {
    collectionExists = mockCollectionExists;
  },
}));
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

const { config } = loadConfig({ QDRANT_URL: 'http://qdrant.test', QDRANT_COLLECTION: 'chunks' });

beforeEach(() => {
  mockCollectionExists.mockResolvedValue({ exists: true });
});

afterEach(async () => {
  await closeInfraClients();
});

describe('infrastructure clients', () => {
  it('refuses access before the boot has created them', () => {
    expect(() => getInfraClients()).toThrow('Infrastructure clients not initialized');
  });

  it('shares the clients created at boot, once the configured collection is found', async () => {
    await initInfraClients(config);

    expect(getInfraClients().mongo).toBe(mockMongo);
    expect(mockCollectionExists).toHaveBeenCalledWith('chunks');
  });

  it('refuses to boot when the configured collection does not exist', async () => {
    mockCollectionExists.mockResolvedValue({ exists: false });

    await expect(initInfraClients(config)).rejects.toThrow('The Qdrant collection "chunks"');
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
