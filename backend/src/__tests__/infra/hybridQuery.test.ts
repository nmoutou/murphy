import { buildHybridQuery } from '../../infra/hybridQuery';

const INPUT = { question: 'article L52-8 du code électoral', vector: [0.1, 0.2, 0.3], from: 20, size: 10, depth: 100 };

describe('buildHybridQuery', () => {
  it('asks for the given page, at the given depth', () => {
    const body = buildHybridQuery(INPUT);

    expect(body).toMatchObject({ from: 20, size: 10, query: { hybrid: { pagination_depth: 100 } } });
  });

  it('reads only the identity of each document', () => {
    expect(buildHybridQuery(INPUT)._source).toEqual({ includes: ['identifier', 'document_type', 'nature'] });
  });

  it('fuses four lists: lexical, references, passage vectors, title vectors', () => {
    const [lexical, references, passageVectors, titleVectors] = buildHybridQuery(INPUT).query?.hybrid?.queries ?? [];

    expect(JSON.stringify(lexical)).toContain('"passages.text","passages.text.ref"');
    expect(JSON.stringify(lexical)).toContain('"metadata.*.texte"');
    expect(JSON.stringify(references)).not.toContain('.texte');
    expect(passageVectors).toMatchObject({
      nested: { query: { knn: { 'passages.embedding': { vector: INPUT.vector, k: 100, expand_nested_docs: true } } } },
    });
    expect(titleVectors).toEqual({ knn: { title_embedding: { vector: INPUT.vector, k: 100 } } });
  });

  it('names the inner hits of the lexical and vector passages, offsets only', () => {
    const [lexical, , passageVectors] = buildHybridQuery(INPUT).query?.hybrid?.queries ?? [];
    const offsets = ['passages.chunk_id', 'passages.char_start', 'passages.char_end'];

    expect(lexical).toMatchObject({
      bool: { should: [{ nested: { inner_hits: { name: 'lexical', size: 100, _source: offsets } } }, expect.anything()] },
    });
    expect(passageVectors).toMatchObject({ nested: { inner_hits: { name: 'vectoriel', _source: offsets } } });
  });
});
