/**
 * Infrastructure Clients Tests
 * Creation at boot, access, and shutdown of the shared clients
 */

import { closeInfraClients, getInfraClients, initInfraClients } from '../../infra/clients';
import { resolveCollection } from '../../infra/collectionPointer';
import { loadConfig } from '../../config';

const mockMongo = { getClient: () => 'driver-client', close: jest.fn() };

jest.mock('../../infra/mongodb', () => ({ MongoDbClient: { connect: async () => mockMongo } }));
jest.mock('../../infra/collectionPointer', () => ({ resolveCollection: jest.fn() }));
jest.mock('@qdrant/qdrant-js', () => ({ QdrantClient: class {} }));
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

const { config } = loadConfig({ QDRANT_URL: 'http://qdrant.test', QDRANT_COLLECTION: 'fallback' });

afterEach(async () => {
  await closeInfraClients();
});

describe('infrastructure clients', () => {
  it('refuses access before the boot has created them', () => {
    expect(() => getInfraClients()).toThrow('Infrastructure clients not initialized');
  });

  it('shares the clients created at boot, on the resolved collection', async () => {
    jest.mocked(resolveCollection).mockResolvedValue('9424808d');

    await initInfraClients(config);

    expect(getInfraClients().mongo).toBe(mockMongo);
    expect(resolveCollection).toHaveBeenCalledWith({
      mongoClient: 'driver-client',
      metaDatabase: 'MURPHY_META',
      qdrantUrl: 'http://qdrant.test',
      fallbackCollection: 'fallback',
    });
  });

  it('closes MongoDB at shutdown, then refuses access again', async () => {
    jest.mocked(resolveCollection).mockResolvedValue('9424808d');
    await initInfraClients(config);

    await closeInfraClients();

    expect(mockMongo.close).toHaveBeenCalled();
    expect(() => getInfraClients()).toThrow('Infrastructure clients not initialized');
  });

  it('does nothing when closing clients that were never created', async () => {
    await expect(closeInfraClients()).resolves.toBeUndefined();
  });
});
