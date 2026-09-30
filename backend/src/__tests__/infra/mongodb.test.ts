/**
 * MongoDB Client Tests
 * The read of the parent documents by their key, over a mocked driver
 */

import type { MongoConfig } from '../../config';
import { MongoDbClient } from '../../infra/mongodb';

const mockFind = jest.fn();
const mockToArray = jest.fn();

// A class, not a `jest.fn`: `restoreMocks` would reset its implementation between tests
jest.mock('mongodb', () => ({
  MongoClient: class {
    async connect() {
      return this;
    }
    db() {
      return {
        admin: () => ({ ping: async () => ({ ok: 1 }) }),
        collection: () => ({ find: mockFind }),
      };
    }
  },
}));
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

const SETTINGS: MongoConfig = {
  uri: 'mongodb://mongo.test:27017',
  database: 'LEGIFRANCE',
  timeoutMs: 1000,
};
const RECORD = { identifier: 'LEGIARTI1', title: 'L2122-22', content: 'Le maire peut…' };
const IDENTIFIER = 'LEGIARTI1';

beforeEach(() => {
  mockFind.mockReturnValue({ project: () => ({ toArray: mockToArray }) });
  mockToArray.mockResolvedValue([RECORD]);
});

describe('MongoDbClient.fetchParentDocuments', () => {
  it('reads each distinct parent once, by identifier', async () => {
    const mongo = await MongoDbClient.connect(SETTINGS);

    const documents = await mongo.fetchParentDocuments([IDENTIFIER, IDENTIFIER, 'JURITEXT2']);

    expect(mockFind).toHaveBeenCalledWith({ identifier: { $in: ['LEGIARTI1', 'JURITEXT2'] } });
    expect(documents).toEqual([{ identifier: 'LEGIARTI1', title: 'L2122-22', content: 'Le maire peut…' }]);
  });

  it('reports a stored document without content as a contract violation', async () => {
    mockToArray.mockResolvedValue([{ ...RECORD, content: undefined }]);
    const mongo = await MongoDbClient.connect(SETTINGS);

    await expect(mongo.fetchParentDocuments([IDENTIFIER])).rejects.toMatchObject({ stage: 'retrieval', code: 'CONTRACT_VIOLATION' });
  });

  it('fails with a retrieval RagError when the query fails', async () => {
    mockToArray.mockRejectedValue(new Error('connection reset'));
    const mongo = await MongoDbClient.connect(SETTINGS);

    await expect(mongo.fetchParentDocuments([IDENTIFIER])).rejects.toMatchObject({
      stage: 'retrieval',
      code: 'DB_FETCH_FAILED',
      message: 'Failed to fetch parent documents from MongoDB: connection reset',
    });
  });
});
