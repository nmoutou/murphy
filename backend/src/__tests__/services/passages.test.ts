/**
 * Passages Tests
 * Code point offsets (the ingestion's unit) turned into UTF-16 highlights, and the
 * join of each chunk to its parent document
 */

import type { RetrievedChunk, StoredDocument } from '../../types/rag';
import { assemblePassages, toUtf16Range } from '../../services/passages';

/** `𝔸` is outside the Basic Multilingual Plane: one code point, two UTF-16 units */
const ASTRAL_PREFIX = '𝔸 ';
const PASSAGE = 'Les actions personnelles se prescrivent par cinq ans.';
const CONTENT = `${ASTRAL_PREFIX}Article 2224. ${PASSAGE}`;
/** Where `PASSAGE` starts, counted as Python counts it */
const PASSAGE_CODE_POINT_START = [...`${ASTRAL_PREFIX}Article 2224. `].length;

const DOCUMENT: StoredDocument = {
  identifier: 'LEGIARTI000006419304',
  title: '2224',
  content: CONTENT,
};

const chunk = (overrides: Partial<RetrievedChunk> = {}): RetrievedChunk => ({
  chunkId: 'LEGIARTI000006419304_0001',
  identifier: DOCUMENT.identifier,
  charStart: PASSAGE_CODE_POINT_START,
  charEnd: PASSAGE_CODE_POINT_START + PASSAGE.length,
  score: 0.9,
  documentType: 'article',
  ...overrides,
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

describe('assemblePassages', () => {
  it('cuts each passage out of its parent, in ranking order', () => {
    const second = chunk({ chunkId: 'LEGIARTI000006419304_0000', charStart: 0, charEnd: 1, score: 0.5 });

    const passages = assemblePassages([chunk(), second], [DOCUMENT]);

    expect(passages.map((passage) => passage.text)).toEqual([PASSAGE, '𝔸']);
    expect(passages[0]).toMatchObject({ document: DOCUMENT, highlightStart: PASSAGE_CODE_POINT_START + 1 });
    expect(passages[1].document).toBe(passages[0].document);
  });

  it('reports a chunk without parent document, naming it', () => {
    expect(() => assemblePassages([chunk({ identifier: 'LEGIARTI000000000404' })], [DOCUMENT])).toThrow(
      expect.objectContaining({ code: 'CONTRACT_VIOLATION', message: expect.stringContaining('LEGIARTI000006419304_0001') }),
    );
  });

  it('reports offsets outside the parent content, naming the chunk', () => {
    expect(() => assemblePassages([chunk({ charEnd: CONTENT.length + 10 })], [DOCUMENT])).toThrow(
      expect.objectContaining({ code: 'CONTRACT_VIOLATION', message: expect.stringContaining('LEGIARTI000006419304_0001') }),
    );
  });
});
