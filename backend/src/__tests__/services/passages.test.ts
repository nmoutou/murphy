import type { PassageRef, RetrievedDocument, StoredDocument } from '../../types/rag';
import { assembleDocuments, toUtf16Range } from '../../services/passages';

/** `𝔸` est hors du plan multilingue de base : un point de code, deux unités UTF-16 */
const ASTRAL_PREFIX = '𝔸 ';
const PASSAGE = 'Les actions personnelles se prescrivent par cinq ans.';
const CONTENT = `${ASTRAL_PREFIX}Article 2224. ${PASSAGE}`;
/** Début de `PASSAGE`, compté comme en Python */
const PASSAGE_CODE_POINT_START = [...`${ASTRAL_PREFIX}Article 2224. `].length;

const DOCUMENT: StoredDocument = {
  identifier: 'LEGIARTI000006419304',
  title: '2224',
  content: CONTENT,
};

const passageRef = (overrides: Partial<PassageRef> = {}): PassageRef => ({
  chunkId: 'LEGIARTI000006419304_0001',
  charStart: PASSAGE_CODE_POINT_START,
  charEnd: PASSAGE_CODE_POINT_START + PASSAGE.length,
  ...overrides,
});

const retrieved = (passages: PassageRef[], identifier = DOCUMENT.identifier): RetrievedDocument => ({
  identifier,
  documentType: 'article',
  passages,
});

describe('toUtf16Range', () => {
  it('shifts the offsets by one unit per astral character before them', () => {
    const range = toUtf16Range(CONTENT, PASSAGE_CODE_POINT_START, PASSAGE_CODE_POINT_START + PASSAGE.length);

    expect(range).toEqual({ start: PASSAGE_CODE_POINT_START + 1, end: PASSAGE_CODE_POINT_START + 1 + PASSAGE.length });
    expect(CONTENT.slice(range?.start, range?.end)).toBe(PASSAGE);
  });

  it('counts an astral character inside the range as two units', () => {
    expect(toUtf16Range(CONTENT, 0, 1)).toEqual({ start: 0, end: 2 });
  });

  it('accepts a range that ends with the content', () => {
    const codePointCount = [...CONTENT].length;

    expect(toUtf16Range(CONTENT, codePointCount - 1, codePointCount)).toEqual({ start: CONTENT.length - 1, end: CONTENT.length });
  });

  it.each([
    ['past the content', 0, [...CONTENT].length + 1],
    ['empty', 3, 3],
    ['reversed', 5, 2],
    ['negative', -1, 2],
  ])('refuses a range %s', (_case, charStart, charEnd) => {
    expect(toUtf16Range(CONTENT, charStart, charEnd)).toBeUndefined();
  });
});

describe('assembleDocuments', () => {
  it('cuts each passage out of its document, in ranking order', () => {
    const second = passageRef({ chunkId: 'LEGIARTI000006419304_0000', charStart: 0, charEnd: 1 });

    const [found] = assembleDocuments([retrieved([passageRef(), second])], [DOCUMENT]);

    expect(found).toMatchObject({ document: DOCUMENT, documentType: 'article' });
    expect(found.passages.map((passage) => passage.text)).toEqual([PASSAGE, '𝔸']);
    expect(found.passages[0]).toMatchObject({ ref: passageRef(), highlightStart: PASSAGE_CODE_POINT_START + 1 });
  });

  it('keeps the ranking of the documents, not the order MongoDB returns them in', () => {
    const other: StoredDocument = { identifier: 'LEGISCTA000006114781', title: 'Chapitre III', content: '' };

    const found = assembleDocuments([retrieved([], other.identifier), retrieved([passageRef()])], [DOCUMENT, other]);

    expect(found.map(({ document }) => document.identifier)).toEqual([other.identifier, DOCUMENT.identifier]);
    expect(found[0].passages).toEqual([]);
  });

  it('reports a document missing from MongoDB, naming it', () => {
    expect(() => assembleDocuments([retrieved([passageRef()], 'LEGIARTI000000000404')], [DOCUMENT])).toThrow(
      expect.objectContaining({ code: 'CONTRACT_VIOLATION', message: expect.stringContaining('LEGIARTI000000000404') }),
    );
  });

  it('reports offsets outside the document content, naming the chunk', () => {
    expect(() => assembleDocuments([retrieved([passageRef({ charEnd: CONTENT.length + 10 })])], [DOCUMENT])).toThrow(
      expect.objectContaining({ code: 'CONTRACT_VIOLATION', message: expect.stringContaining('LEGIARTI000006419304_0001') }),
    );
  });
});
