import { toSearchHit } from '../../infra/searchHits';

const passage = (ordinal: number) => ({
  chunk_id: `CETATEXT000054320839_${String(ordinal).padStart(4, '0')}`,
  char_start: ordinal * 100,
  char_end: ordinal * 100 + 384,
});
const ref = (ordinal: number) => ({
  chunkId: `CETATEXT000054320839_${String(ordinal).padStart(4, '0')}`,
  charStart: ordinal * 100,
  charEnd: ordinal * 100 + 384,
});
const innerHits = (...ordinals: number[]) => ({
  hits: { hits: ordinals.map((ordinal) => ({ _nested: { field: 'passages', offset: ordinal }, _source: passage(ordinal) })) },
});

/** Une réponse d'OpenSearch 3.9, réduite aux champs lus */
const HIT = {
  _index: 'documents',
  _id: 'CETATEXT000054320839',
  _score: 0.027,
  _source: {
    identifier: 'CETATEXT000054320839',
    document_type: 'decision',
    nature: 'ARRET',
  },
  inner_hits: { lexical: innerHits(2, 0), vectoriel: innerHits(1) },
};

describe('toSearchHit', () => {
  it('reads the document and its matching passages in rank order', () => {
    expect(toSearchHit(HIT)).toEqual({
      identifier: 'CETATEXT000054320839',
      documentType: 'decision',
      nature: 'ARRET',
      lexicalPassages: [ref(2), ref(0)],
      vectorPassages: [ref(1)],
    });
  });

  it('reads a section found by its title: no nature, no passage, no inner hit', () => {
    const section = {
      _id: 'LEGISCTA000006114781',
      _source: { identifier: 'LEGISCTA000006114781', nature: null, document_type: 'section' },
      inner_hits: { lexical: innerHits(), vectoriel: innerHits() },
    };

    expect(toSearchHit(section)).toEqual({
      identifier: 'LEGISCTA000006114781',
      documentType: 'section',
      nature: undefined,
      lexicalPassages: [],
      vectorPassages: [],
    });
  });

  it('accepts a hit without inner hits', () => {
    expect(toSearchHit({ ...HIT, inner_hits: undefined })).toMatchObject({ lexicalPassages: [], vectorPassages: [] });
  });

  it.each([
    ['an unknown document type', { ...HIT, _source: { ...HIT._source, document_type: 'loi' } }, '_source.document_type'],
    [
      'a passage without offsets',
      { ...HIT, inner_hits: { vectoriel: { hits: { hits: [{ _source: { chunk_id: 'c' } }] } } } },
      'inner_hits.vectoriel',
    ],
    [
      'an inner hit with a fractional offset',
      { ...HIT, inner_hits: { lexical: { hits: { hits: [{ _source: { ...passage(0), char_end: 1.5 } }] } } } },
      'inner_hits.lexical',
    ],
  ])('reports %s as a contract violation, naming the document', (_case, hit, field) => {
    expect(() => toSearchHit(hit)).toThrow(
      expect.objectContaining({
        code: 'CONTRACT_VIOLATION',
        message: expect.stringMatching(new RegExp(`CETATEXT000054320839 .*${field.replace(/[.*]/g, '\\$&')}`)),
      }),
    );
  });

  it('reports a hit without source, even without id', () => {
    expect(() => toSearchHit({})).toThrow(expect.objectContaining({ message: expect.stringContaining('<unknown>') }));
  });
});
