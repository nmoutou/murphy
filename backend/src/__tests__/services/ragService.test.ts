import type { FoundDocument, Passage, RetrievedDocument, SearchHit, StoredDocument } from '../../types/rag';
import { embedQuestion, fetchDocuments, retrieveDocuments } from '../../services/ragService';
import { getInfraClients } from '../../infra/clients';

jest.mock('../../infra/clients', () => {
  const clients = {
    embedding: { embedQuestion: jest.fn() },
    opensearch: { search: jest.fn() },
    mongo: { fetchParentDocuments: jest.fn() },
  };
  return { getInfraClients: () => clients };
});
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

const EMBEDDING = [0.1, 0.2, 0.3];
const DOCUMENT: StoredDocument = {
  identifier: 'LEGIARTI000006419304',
  title: 'Code civil, art. 2224',
  content: 'Article 2224. Cinq ans.',
};
const PASSAGE_REF = { chunkId: 'LEGIARTI000006419304_0001', charStart: 14, charEnd: 23 };
const RETRIEVED: RetrievedDocument = { identifier: DOCUMENT.identifier, documentType: 'article', passages: [PASSAGE_REF] };
const PASSAGE: Passage = { ref: PASSAGE_REF, text: 'Cinq ans.', highlightStart: 14, highlightEnd: 23 };
const FOUND: FoundDocument = { document: DOCUMENT, documentType: 'article', passages: [PASSAGE] };

const { embedding, opensearch, mongo } = getInfraClients();


describe('fetchDocuments', () => {
  it('skips MongoDB when no document was found', async () => {
    await expect(fetchDocuments([])).resolves.toEqual({ documents: [], docFetchMs: 0 });
    expect(mongo.fetchParentDocuments).not.toHaveBeenCalled();
  });

  it('reads the documents and cuts their passages out', async () => {
    jest.mocked(mongo.fetchParentDocuments).mockResolvedValue([DOCUMENT]);

    const fetched = await fetchDocuments([RETRIEVED]);

    expect(mongo.fetchParentDocuments).toHaveBeenCalledWith([DOCUMENT.identifier]);
    expect(fetched.documents).toEqual([FOUND]);
    expect(fetched.docFetchMs).toBeGreaterThanOrEqual(0);
  });

  it('refuses a document missing from MongoDB', async () => {
    jest.mocked(mongo.fetchParentDocuments).mockResolvedValue([]);

    await expect(fetchDocuments([RETRIEVED])).rejects.toMatchObject({ code: 'CONTRACT_VIOLATION' });
  });
});

describe('embedQuestion', () => {
  it('returns the embedding with the stage duration', async () => {
    jest.mocked(embedding.embedQuestion).mockResolvedValue(EMBEDDING);

    const embedded = await embedQuestion('Quel délai ?');

    expect(embedding.embedQuestion).toHaveBeenCalledWith('Quel délai ?');
    expect(embedded.embedding).toBe(EMBEDDING);
    expect(embedded.embeddingMs).toBeGreaterThanOrEqual(0);
  });
});

describe('retrieveDocuments', () => {
  it('searches with the question, its vector and the page window, and ranks the passages of each document', async () => {
    const hit: SearchHit = {
      identifier: DOCUMENT.identifier,
      documentType: 'article',
      lexicalPassages: [PASSAGE_REF],
      vectorPassages: [],
    };
    jest.mocked(opensearch.search).mockResolvedValue([hit]);

    const retrieved = await retrieveDocuments('Quel délai ?', EMBEDDING, { from: 20, size: 10 });

    expect(opensearch.search).toHaveBeenCalledWith('Quel délai ?', EMBEDDING, { from: 20, size: 10 });
    expect(retrieved.documents).toEqual([RETRIEVED]);
    expect(retrieved.retrievalMs).toBeGreaterThanOrEqual(0);
  });
});
