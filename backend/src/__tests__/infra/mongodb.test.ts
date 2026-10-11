import type { MongoConfig } from '../../config';
import { MongoDbClient } from '../../infra/mongodb';

const mockFind = jest.fn();
const mockFindOne = jest.fn();
const mockToArray = jest.fn();
const mockProject = jest.fn();

// Une classe, pas un `jest.fn` : `restoreMocks` réinitialiserait son implémentation entre les tests
jest.mock('mongodb', () => ({
  MongoClient: class {
    async connect() {
      return this;
    }
    db() {
      return {
        admin: () => ({ ping: async () => ({ ok: 1 }) }),
        collection: () => ({ find: mockFind, findOne: mockFindOne }),
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
  database: 'MURPHY_DATA',
  timeoutMs: 1000,
};
const RECORD = { identifier: 'LEGIARTI1', title: 'L2122-22', content: 'Le maire peut…' };
const IDENTIFIER = 'LEGIARTI1';

beforeEach(() => {
  mockProject.mockReturnValue({ toArray: mockToArray });
  mockFind.mockReturnValue({ project: mockProject });
  mockToArray.mockResolvedValue([RECORD]);
});

describe('MongoDbClient.fetchParentDocuments', () => {
  it('reads each distinct parent once, by identifier', async () => {
    const mongo = await MongoDbClient.connect(SETTINGS);

    const documents = await mongo.fetchParentDocuments([IDENTIFIER, IDENTIFIER, 'JURITEXT2']);

    expect(mockFind).toHaveBeenCalledWith({ identifier: { $in: ['LEGIARTI1', 'JURITEXT2'] } });
    expect(documents).toEqual([{ identifier: 'LEGIARTI1', title: 'L2122-22', content: 'Le maire peut…' }]);
  });

  it('reads the DILA status of a document that has one', async () => {
    mockToArray.mockResolvedValue([{ ...RECORD, metadata: { statut: 'VIGUEUR', nature: 'Article' } }]);
    const mongo = await MongoDbClient.connect(SETTINGS);

    const [document] = await mongo.fetchParentDocuments([IDENTIFIER]);

    expect(mockProject).toHaveBeenCalledWith(expect.objectContaining({ content: 1, 'metadata.statut': 1 }));
    expect(document).toEqual({ ...RECORD, status: 'VIGUEUR' });
  });

  it('reports a status that is not a string as a contract violation', async () => {
    mockToArray.mockResolvedValue([{ ...RECORD, metadata: { statut: ['VIGUEUR'] } }]);
    const mongo = await MongoDbClient.connect(SETTINGS);

    await expect(mongo.fetchParentDocuments([IDENTIFIER])).rejects.toMatchObject({ code: 'CONTRACT_VIOLATION' });
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

describe('MongoDbClient.fetchDocument', () => {
  it('reads one document by identifier, its identity, title and text only', async () => {
    mockFindOne.mockResolvedValue(RECORD);
    const mongo = await MongoDbClient.connect(SETTINGS);

    await expect(mongo.fetchDocument(IDENTIFIER)).resolves.toEqual(RECORD);
    expect(mockFindOne).toHaveBeenCalledWith(
      { identifier: IDENTIFIER },
      { projection: { _id: 0, identifier: 1, title: 1, content: 1 } },
    );
  });

  it('returns undefined for an unknown identifier', async () => {
    mockFindOne.mockResolvedValue(null);
    const mongo = await MongoDbClient.connect(SETTINGS);

    await expect(mongo.fetchDocument('LEGIARTI0')).resolves.toBeUndefined();
  });

  it('reports a stored document without title as a contract violation', async () => {
    mockFindOne.mockResolvedValue({ ...RECORD, title: null });
    const mongo = await MongoDbClient.connect(SETTINGS);

    await expect(mongo.fetchDocument(IDENTIFIER)).rejects.toMatchObject({ code: 'CONTRACT_VIOLATION' });
  });

  it('fails with a retrieval RagError when the query fails', async () => {
    mockFindOne.mockRejectedValue(new Error('connection reset'));
    const mongo = await MongoDbClient.connect(SETTINGS);

    await expect(mongo.fetchDocument(IDENTIFIER)).rejects.toMatchObject({
      stage: 'retrieval',
      code: 'DB_FETCH_FAILED',
      message: 'Failed to fetch a document from MongoDB: connection reset',
    });
  });
});
