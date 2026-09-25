/**
 * Collection Pointer Tests
 * Which Qdrant collection the backend serves, and its refusal to boot on a missing one
 */

import type { MongoClient } from 'mongodb';
import { resolveCollection } from '../../infra/collectionPointer';

const mockCollectionExists = jest.fn();
const mockGetCollection = jest.fn();

jest.mock('@qdrant/qdrant-js', () => ({
  QdrantClient: class {
    collectionExists = mockCollectionExists;
    getCollection = mockGetCollection;
  },
}));
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

const FALLBACK_COLLECTION = 'chunks';
const PUBLISHED = {
  collection_name: '9424808d',
  fingerprint: '9424808d',
  run_id: 'run-1',
  document_count: 12,
  published_at: '2026-09-01T00:00:00Z',
};

/** Only `db().collection().findOne()` is read: a partial double, hence the cast from `unknown` */
const mongoClientFinding = (findOne: () => Promise<unknown>): MongoClient => {
  const double: unknown = { db: () => ({ collection: () => ({ findOne }) }) };
  return double as MongoClient;
};

const sourcesWith = (findOne: () => Promise<unknown>) => ({
  mongoClient: mongoClientFinding(findOne),
  metaDatabase: 'MURPHY_META',
  qdrantUrl: 'http://qdrant.test',
  fallbackCollection: FALLBACK_COLLECTION,
});

beforeEach(() => {
  mockCollectionExists.mockResolvedValue({ exists: true });
  mockGetCollection.mockResolvedValue({ points_count: 12 });
});

describe('resolveCollection', () => {
  it('serves the collection published by the last ok run', async () => {
    await expect(resolveCollection(sourcesWith(async () => PUBLISHED))).resolves.toBe('9424808d');
    expect(mockCollectionExists).toHaveBeenCalledWith('9424808d');
  });

  it.each([
    ['no run has published', async () => null],
    ['the pointer cannot be read', async () => Promise.reject(new Error('MongoDB unreachable'))],
  ])('falls back on QDRANT_COLLECTION when %s', async (_case, findOne) => {
    await expect(resolveCollection(sourcesWith(findOne))).resolves.toBe(FALLBACK_COLLECTION);
  });

  it('refuses a collection that does not exist', async () => {
    mockCollectionExists.mockResolvedValue({ exists: false });

    await expect(resolveCollection(sourcesWith(async () => null))).rejects.toThrow(
      "La collection Qdrant « chunks » n'existe pas",
    );
  });

  it('refuses to boot when Qdrant cannot be reached', async () => {
    mockCollectionExists.mockRejectedValue(new Error('connect ECONNREFUSED'));

    await expect(resolveCollection(sourcesWith(async () => PUBLISHED))).rejects.toThrow('Qdrant injoignable');
  });
});
