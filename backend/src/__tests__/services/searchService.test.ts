import type { SearchHit, StoredDocument } from '../../types/rag';
import { PAGE_COUNT, searchDocuments } from '../../services/searchService';
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

describe('searchDocuments', () => {
  it('counts the pages that fit in the depth', () => {
    expect(PAGE_COUNT).toBe(10);
  });

  it('serves the documents in rank order, each with its matching passages', async () => {
    const response = await searchDocuments({ question: QUESTION, page: 1 });

    expect(response).toEqual({
      page: 1,
      pageCount: 10,
      results: [
        {
          identifier: ARTICLE.identifier,
          title: 'Code civil, art. 2224',
          documentType: 'article',
          nature: undefined,
          passages: [{ chunkId: PASSAGE_REF.chunkId, text: 'Cinq ans.', start: 14, end: 23 }],
        },
        { identifier: SECTION.identifier, title: 'Chapitre III', documentType: 'section', nature: undefined, passages: [] },
      ],
    });
  });

  it('searches from the first rank of the page', async () => {
    await searchDocuments({ question: QUESTION, page: 3 });

    expect(embedding.embedQuestion).toHaveBeenCalledWith(QUESTION);
    expect(opensearch.search).toHaveBeenCalledWith(QUESTION, EMBEDDING, 20);
  });

  it('serves an empty page past the documents found, up to the last page', async () => {
    jest.mocked(opensearch.search).mockResolvedValue([]);

    await expect(searchDocuments({ question: QUESTION, page: 10 })).resolves.toEqual({ page: 10, pageCount: 10, results: [] });
    expect(opensearch.search).toHaveBeenCalledWith(QUESTION, EMBEDDING, 90);
  });

  it('refuses a page beyond the last one, before any search', async () => {
    const search = searchDocuments({ question: QUESTION, page: 11 });

    await expect(search).rejects.toBeInstanceOf(RagError);
    await expect(search).rejects.toMatchObject({ code: 'PAGE_OUT_OF_RANGE' });
    expect(embedding.embedQuestion).not.toHaveBeenCalled();
  });
});
