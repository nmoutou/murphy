import type { FoundDocument, Passage, RetrievedDocument, SearchHit, StoredDocument } from '../../types/rag';
import {
  MAX_LLM_CONTEXT_CHARS,
  buildContextString,
  embedQuestion,
  fetchDocuments,
  retrieveDocuments,
} from '../../services/ragService';
import { getInfraClients } from '../../infra/clients';
import { logger } from '../../utils/logger';

jest.mock('../../infra/clients', () => {
  const clients = {
    embedding: { embedText: jest.fn() },
    opensearch: { search: jest.fn() },
    mongo: { fetchParentDocuments: jest.fn() },
    llm: { stream: jest.fn() },
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

const foundWith = (title: string, texts: string[]): FoundDocument => ({
  document: { ...DOCUMENT, title },
  documentType: 'article',
  passages: texts.map((text) => ({ ...PASSAGE, text })),
});

describe('buildContextString', () => {
  it('says so when no passage was found', () => {
    expect(buildContextString([])).toBe('Aucun document pertinent trouvé.');
    expect(buildContextString([foundWith('Chapitre III', [])])).toBe('Aucun document pertinent trouvé.');
  });

  it('numbers the passages across documents and gives each passage alone', () => {
    const second = foundWith('Code civil, art. 2225', ['Dix ans.', 'Vingt ans.']);

    expect(buildContextString([FOUND, second])).toBe(
      '[1] Code civil, art. 2224\nCinq ans.\n\n[2] Code civil, art. 2225\nDix ans.\n\n[3] Code civil, art. 2225\nVingt ans.',
    );
  });

  it('stops before the passage that would exceed the cap, and logs it', () => {
    // Chaque bloc fait 100 000 caractères : « [n] T\n » (6) + le texte
    const text = 'x'.repeat(MAX_LLM_CONTEXT_CHARS / 2 - 6);
    const found = foundWith('T', [text, text, 'court']);

    const context = buildContextString([found]);

    expect(context).toBe(`[1] T\n${text}`);
    expect(logger.warn).toHaveBeenCalledWith(expect.objectContaining({ kept: 1, dropped: 2 }), expect.any(String));
  });

  it('keeps a context exactly at the cap', () => {
    const text = 'x'.repeat(MAX_LLM_CONTEXT_CHARS - '[1] T\n'.length);

    expect(buildContextString([foundWith('T', [text])])).toHaveLength(MAX_LLM_CONTEXT_CHARS);
  });
});

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
    jest.mocked(embedding.embedText).mockResolvedValue(EMBEDDING);

    const embedded = await embedQuestion('Quel délai ?');

    expect(embedding.embedText).toHaveBeenCalledWith('Quel délai ?');
    expect(embedded.embedding).toBe(EMBEDDING);
    expect(embedded.embeddingMs).toBeGreaterThanOrEqual(0);
  });
});

describe('retrieveDocuments', () => {
  it('searches with the question, its vector and the page offset, and ranks the passages of each document', async () => {
    const hit: SearchHit = {
      identifier: DOCUMENT.identifier,
      documentType: 'article',
      lexicalPassages: [PASSAGE_REF],
      vectorPassages: [],
    };
    jest.mocked(opensearch.search).mockResolvedValue([hit]);

    const retrieved = await retrieveDocuments('Quel délai ?', EMBEDDING, 20);

    expect(opensearch.search).toHaveBeenCalledWith('Quel délai ?', EMBEDDING, 20);
    expect(retrieved.documents).toEqual([RETRIEVED]);
    expect(retrieved.retrievalMs).toBeGreaterThanOrEqual(0);
  });
});
