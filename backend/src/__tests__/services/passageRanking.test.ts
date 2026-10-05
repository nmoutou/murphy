import type { PassageRef, SearchHit } from '../../types/rag';
import { toRetrievedDocument } from '../../services/passageRanking';

const ref = (ordinal: number): PassageRef => ({
  chunkId: `CETATEXT000054320839_${String(ordinal).padStart(4, '0')}`,
  charStart: ordinal * 100,
  charEnd: ordinal * 100 + 384,
});

const hit = (overrides: Partial<SearchHit> = {}): SearchHit => ({
  identifier: 'CETATEXT000054320839',
  documentType: 'decision',
  nature: 'ARRET',
  lexicalPassages: [],
  vectorPassages: [],
  allPassages: [ref(0), ref(1), ref(2), ref(3)],
  ...overrides,
});

describe('toRetrievedDocument', () => {
  it('keeps the identity of the document', () => {
    expect(toRetrievedDocument(hit())).toMatchObject({
      identifier: 'CETATEXT000054320839',
      documentType: 'decision',
      nature: 'ARRET',
    });
  });

  it('puts first a passage found by both lists, then alternates their ranks', () => {
    const retrieved = toRetrievedDocument(hit({ lexicalPassages: [ref(3), ref(1)], vectorPassages: [ref(2), ref(1)] }));

    // ref(1) : 1/62 + 1/62 ; ref(3) et ref(2) : 1/61 chacun, le lexical d'abord
    expect(retrieved.passages).toEqual([ref(1), ref(3), ref(2)]);
  });

  it('gives a passage found by both lists once', () => {
    const retrieved = toRetrievedDocument(hit({ lexicalPassages: [ref(2)], vectorPassages: [ref(2)] }));

    expect(retrieved.passages).toEqual([ref(2)]);
  });

  it('keeps the order of a single list', () => {
    const retrieved = toRetrievedDocument(hit({ vectorPassages: [ref(3), ref(0), ref(2)] }));

    expect(retrieved.passages).toEqual([ref(3), ref(0), ref(2)]);
  });

  it('gives all its passages, in text order, to a document found without matching passage', () => {
    expect(toRetrievedDocument(hit()).passages).toEqual([ref(0), ref(1), ref(2), ref(3)]);
  });

  it('gives no passage to a section', () => {
    expect(toRetrievedDocument(hit({ documentType: 'section', allPassages: [] })).passages).toEqual([]);
  });
});
