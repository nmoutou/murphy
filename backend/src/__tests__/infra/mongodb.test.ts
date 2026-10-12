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
const RECORD = { identifier: 'LEGIARTI1', title: 'L2122-22', content: 'Le maire peut…', content_length: 14 };
const STORED = { identifier: 'LEGIARTI1', title: 'L2122-22', content: 'Le maire peut…', contentLength: 14 };
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
    expect(documents).toEqual([STORED]);
  });

  it('reads the DILA status of a document that has one', async () => {
    mockToArray.mockResolvedValue([{ ...RECORD, metadata: { statut: 'VIGUEUR', nature: 'Article' } }]);
    const mongo = await MongoDbClient.connect(SETTINGS);

    const [document] = await mongo.fetchParentDocuments([IDENTIFIER]);

    expect(mockProject).toHaveBeenCalledWith(expect.objectContaining({ content: 1, 'metadata.statut': 1 }));
    expect(document).toEqual({ ...STORED, status: 'VIGUEUR' });
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

    await expect(mongo.fetchDocument(IDENTIFIER)).resolves.toEqual(STORED);
    expect(mockFindOne).toHaveBeenCalledWith(
      { identifier: IDENTIFIER },
      { projection: { _id: 0, identifier: 1, title: 1, content: 1, content_length: 1 } },
    );
  });

  it('returns undefined for an unknown identifier', async () => {
    mockFindOne.mockResolvedValue(null);
    const mongo = await MongoDbClient.connect(SETTINGS);

    await expect(mongo.fetchDocument('LEGIARTI0')).resolves.toBeUndefined();
  });

  it.each([
    ['without content_length', undefined],
    ['with a negative content_length', -1],
    ['with a fractional content_length', 1.5],
  ])('reports a stored document %s as a contract violation, as before a re-ingestion', async (_case, contentLength) => {
    mockFindOne.mockResolvedValue({ ...RECORD, content_length: contentLength });
    const mongo = await MongoDbClient.connect(SETTINGS);

    await expect(mongo.fetchDocument(IDENTIFIER)).rejects.toMatchObject({ code: 'CONTRACT_VIOLATION' });
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

describe('MongoDbClient.fetchExplainedDocuments', () => {
  const DECISION = {
    identifier: 'JURITEXT2',
    title: 'Cour de cassation, 6 mars 2008',
    content: 'LA COUR…',
    content_length: 8,
    document_type: 'decision',
    nature: 'ARRET',
    metadata: { juridiction: 'Cour de cassation' },
  };
  const ARTICLE = {
    ...RECORD,
    document_type: 'article',
    nature: null,
    parent_text_title: ['Code général des collectivités territoriales'],
    metadata: { statut: 'VIGUEUR', versions_a_venir: ['2222-02-22'] },
  };

  it('reads the documents in the order of the selection, with only the named metadata', async () => {
    mockToArray.mockResolvedValue([DECISION, ARTICLE]);
    const mongo = await MongoDbClient.connect(SETTINGS);

    const documents = await mongo.fetchExplainedDocuments(['LEGIARTI1', 'JURITEXT2'], ['statut', 'versions_a_venir', 'juridiction']);

    expect(mockFind).toHaveBeenCalledWith({ identifier: { $in: ['LEGIARTI1', 'JURITEXT2'] } });
    expect(mockProject).toHaveBeenCalledWith(expect.objectContaining({
      'metadata.statut': 1,
      'metadata.versions_a_venir': 1,
      'metadata.juridiction': 1,
      parent_text_title: 1,
    }));
    expect(mockProject.mock.calls[0][0]).not.toHaveProperty('metadata');
    expect(documents.map(({ identifier }) => identifier)).toEqual(['LEGIARTI1', 'JURITEXT2']);
    expect(documents[0]).toEqual({
      identifier: 'LEGIARTI1',
      title: 'L2122-22',
      content: 'Le maire peut…',
      documentType: 'article',
      nature: undefined,
      parentTextTitles: ['Code général des collectivités territoriales'],
      metadata: { statut: 'VIGUEUR', versions_a_venir: ['2222-02-22'] },
    });
    expect(documents[1]).toMatchObject({ documentType: 'decision', nature: 'ARRET', parentTextTitles: [] });
  });

  it('refuses a selection with a document that does not exist', async () => {
    mockToArray.mockResolvedValue([ARTICLE]);
    const mongo = await MongoDbClient.connect(SETTINGS);

    await expect(mongo.fetchExplainedDocuments(['LEGIARTI1', 'JURITEXT0'], [])).rejects.toMatchObject({
      stage: 'request',
      code: 'DOCUMENT_NOT_FOUND',
    });
  });

  it.each([
    ['an unknown document type', { document_type: 'livre' }],
    ['a metadata that is neither a string nor a list of strings', { metadata: { statut: { etat: 'VIGUEUR' } } }],
    ['a parent text title that is not a list', { parent_text_title: 'Code civil' }],
  ])('reports %s as a contract violation', async (_case, overrides) => {
    mockToArray.mockResolvedValue([{ ...ARTICLE, ...overrides }]);
    const mongo = await MongoDbClient.connect(SETTINGS);

    await expect(mongo.fetchExplainedDocuments(['LEGIARTI1'], ['statut'])).rejects.toMatchObject({ code: 'CONTRACT_VIOLATION' });
  });

  it('fails with a retrieval RagError when the query fails', async () => {
    mockToArray.mockRejectedValue(new Error('connection reset'));
    const mongo = await MongoDbClient.connect(SETTINGS);

    await expect(mongo.fetchExplainedDocuments(['LEGIARTI1'], [])).rejects.toMatchObject({ stage: 'retrieval', code: 'DB_FETCH_FAILED' });
  });
});
