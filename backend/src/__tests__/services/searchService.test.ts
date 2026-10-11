import type { SearchHit, StoredDocument } from '../../types/rag';
import { searchDocuments, toPageWindow } from '../../services/searchService';
import { getInfraClients } from '../../infra/clients';
import { RagError } from '../../types/rag';

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

const QUESTION = 'Quel délai de prescription ?';
const EMBEDDING = [0.1, 0.2, 0.3];
const ARTICLE: StoredDocument = {
  identifier: 'LEGIARTI000006419304',
  title: 'Code civil, art. 2224',
  content: 'Article 2224. Cinq ans.',
  status: 'VIGUEUR',
};
const SECTION: StoredDocument = { identifier: 'LEGISCTA000006114781', title: 'Chapitre III', content: '' };
const PASSAGE_REF = { chunkId: 'LEGIARTI000006419304_0001', charStart: 14, charEnd: 23 };
const HITS: SearchHit[] = [
  { identifier: ARTICLE.identifier, documentType: 'article', lexicalPassages: [PASSAGE_REF], vectorPassages: [] },
  { identifier: SECTION.identifier, documentType: 'section', lexicalPassages: [], vectorPassages: [] },
];

const { embedding, opensearch, mongo } = getInfraClients();

beforeEach(() => {
  jest.mocked(embedding.embedQuestion).mockResolvedValue(EMBEDDING);
  jest.mocked(opensearch.search).mockResolvedValue(HITS);
  jest.mocked(mongo.fetchParentDocuments).mockResolvedValue([SECTION, ARTICLE]);
});

describe('toPageWindow', () => {
  it('cuts the depth into full pages when the size divides it', () => {
    expect(toPageWindow(3, 10, 100)).toEqual({ from: 20, size: 10, pageCount: 10 });
  });

  it('rounds the page count up and truncates the last page, so no ranked document is lost', () => {
    expect(toPageWindow(1, 30, 100)).toEqual({ from: 0, size: 30, pageCount: 4 });
    expect(toPageWindow(4, 30, 100)).toEqual({ from: 90, size: 10, pageCount: 4 });
  });
});

describe('searchDocuments', () => {
  it('serves the documents in rank order, each with its matching passages and whether it is in force', async () => {
    const response = await searchDocuments({ question: QUESTION, page: 1, pageSize: 10 });

    expect(response).toEqual({
      page: 1,
      pageCount: 10,
      pageSize: 10,
      pageSizes: [10, 25, 50],
      results: [
        {
          identifier: ARTICLE.identifier,
          title: 'Code civil, art. 2224',
          documentType: 'article',
          nature: undefined,
          isInForce: true,
          passages: [{ chunkId: PASSAGE_REF.chunkId, text: 'Cinq ans.', start: 14, end: 23 }],
        },
        {
          identifier: SECTION.identifier,
          title: 'Chapitre III',
          documentType: 'section',
          nature: undefined,
          isInForce: undefined,
          passages: [],
        },
      ],
    });
  });

  it.each([
    ['VIGUEUR_DIFF', false],
    ['MODIFIE', false],
    ['ABROGE', false],
  ])('tells a %s document is not in force', async (status, isInForce) => {
    jest.mocked(mongo.fetchParentDocuments).mockResolvedValue([SECTION, { ...ARTICLE, status }]);

    const { results } = await searchDocuments({ question: QUESTION, page: 1, pageSize: 10 });

    expect(results[0].isInForce).toBe(isInForce);
  });

  it('searches the window of the page, at the requested size', async () => {
    await searchDocuments({ question: QUESTION, page: 3, pageSize: 25 });

    expect(embedding.embedQuestion).toHaveBeenCalledWith(QUESTION);
    expect(opensearch.search).toHaveBeenCalledWith(QUESTION, EMBEDDING, { from: 50, size: 25 });
  });

  it('serves an empty page past the documents found, up to the last page', async () => {
    jest.mocked(opensearch.search).mockResolvedValue([]);

    await expect(searchDocuments({ question: QUESTION, page: 10, pageSize: 10 })).resolves.toMatchObject({
      page: 10,
      pageCount: 10,
      results: [],
    });
    expect(opensearch.search).toHaveBeenCalledWith(QUESTION, EMBEDDING, { from: 90, size: 10 });
  });

  it.each([
    [11, 10],
    [3, 50],
  ])('refuses page %i at %i per page, beyond the last one, before any search', async (page, pageSize) => {
    const search = searchDocuments({ question: QUESTION, page, pageSize });

    await expect(search).rejects.toBeInstanceOf(RagError);
    await expect(search).rejects.toMatchObject({ code: 'PAGE_OUT_OF_RANGE' });
    expect(embedding.embedQuestion).not.toHaveBeenCalled();
  });
});
