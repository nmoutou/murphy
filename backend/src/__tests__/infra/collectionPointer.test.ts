/**
 * Collection Pointer Tests
 * Which Qdrant collection the backend serves, and its refusal to boot on a collection
 * that is not published, not in the contract version it reads, or missing
 */

import type { MongoClient } from 'mongodb';
import { resolveCollection, SERVING_CONTRACT_VERSION } from '../../infra/collectionPointer';

const mockCollectionExists = jest.fn();
const mockGetCollection = jest.fn();
const mockQdrantClientConstructor = jest.fn();

jest.mock('@qdrant/qdrant-js', () => ({
  QdrantClient: class {
    collectionExists = mockCollectionExists;
    getCollection = mockGetCollection;

    constructor(args: unknown) {
      mockQdrantClientConstructor(args);
    }
  },
}));
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

/** A pointer written before ADR-039: no contract version */
const PUBLISHED_BEFORE_THE_CONTRACT = {
  collection_name: '9424808d',
  fingerprint: '9424808d',
  run_id: 'run-1',
  document_count: 12,
  published_at: '2026-09-01T00:00:00Z',
};
const PUBLISHED = { ...PUBLISHED_BEFORE_THE_CONTRACT, serving_contract_version: SERVING_CONTRACT_VERSION };

/** Only `db().collection().findOne()` is read: a partial double, hence the cast from `unknown` */
const mongoClientFinding = (findOne: () => Promise<unknown>): MongoClient => {
  const double: unknown = { db: () => ({ collection: () => ({ findOne }) }) };
  return double as MongoClient;
};

const sourcesWith = (findOne: () => Promise<unknown>) => ({
  mongoClient: mongoClientFinding(findOne),
  metaDatabase: 'MURPHY_META',
  qdrant: { url: 'http://qdrant.test', timeoutMs: 2500 },
});

beforeEach(() => {
  mockCollectionExists.mockResolvedValue({ exists: true });
  mockGetCollection.mockResolvedValue({ points_count: 12 });
});

describe('resolveCollection', () => {
  it('serves the collection published by the last ok run', async () => {
    await expect(resolveCollection(sourcesWith(async () => PUBLISHED))).resolves.toBe('9424808d');
    expect(mockCollectionExists).toHaveBeenCalledWith('9424808d');
    expect(mockQdrantClientConstructor).toHaveBeenCalledWith({ url: 'http://qdrant.test', timeout: 2500 });
  });

  it.each([
    ['no run has published', async () => null, "Aucun run d'ingestion n'a publié de collection"],
    ['the pointer cannot be read', async () => Promise.reject(new Error('MongoDB unreachable')), 'MongoDB unreachable'],
  ])('refuses to boot when %s', async (_case, findOne, message) => {
    await expect(resolveCollection(sourcesWith(findOne))).rejects.toThrow(message);
    expect(mockCollectionExists).not.toHaveBeenCalled();
  });

  it.each([
    ['without version', PUBLISHED_BEFORE_THE_CONTRACT, 'v(aucune)', 'Réingérer le corpus'],
    ['in an older version', { ...PUBLISHED, serving_contract_version: SERVING_CONTRACT_VERSION - 1 }, 'v0', 'Réingérer le corpus'],
    ['in a newer version', { ...PUBLISHED, serving_contract_version: SERVING_CONTRACT_VERSION + 1 }, 'v2', 'Mettre à jour le backend'],
  ])('refuses a collection published %s', async (_case, pointer, version, remedy) => {
    const refusal = resolveCollection(sourcesWith(async () => pointer));

    await expect(refusal).rejects.toThrow(`contrat de serving ${version}`);
    await expect(refusal).rejects.toThrow(remedy);
  });

  it('refuses a published collection that does not exist', async () => {
    mockCollectionExists.mockResolvedValue({ exists: false });

    await expect(resolveCollection(sourcesWith(async () => PUBLISHED))).rejects.toThrow(
      "La collection Qdrant « 9424808d » n'existe pas",
    );
  });

  it('refuses to boot when Qdrant cannot be reached', async () => {
    mockCollectionExists.mockRejectedValue(new Error('connect ECONNREFUSED'));

    await expect(resolveCollection(sourcesWith(async () => PUBLISHED))).rejects.toThrow('Qdrant injoignable');
  });
});
