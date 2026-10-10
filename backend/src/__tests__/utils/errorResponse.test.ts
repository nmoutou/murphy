import { toErrorResponse } from '../../utils/errorResponse';
import { RagError } from '../../types/rag';

describe('toErrorResponse', () => {
  it.each([
    ['request', 'PAGE_OUT_OF_RANGE', 400],
    ['retrieval', 'DOCUMENT_NOT_FOUND', 404],
    ['embedding', 'EMBEDDING_FAILED', 502],
    ['retrieval', 'SEARCH_FAILED', 502],
    ['retrieval', 'DB_FETCH_FAILED', 502],
    ['embedding', 'TIMEOUT', 504],
    ['retrieval', 'CONTRACT_VIOLATION', 500],
  ] as const)('answers a %s RagError %s with a %i', (stage, code, status) => {
    expect(toErrorResponse(new RagError(stage, code, 'detail for the logs'))).toEqual({ status, code });
  });

  it('answers a RagError whose code is not in the contract with a 500 INTERNAL', () => {
    expect(toErrorResponse(new RagError('llm', 'API_ERROR', 'LLM down'))).toEqual({ status: 500, code: 'INTERNAL' });
  });

  it('answers any other error with a 500 INTERNAL', () => {
    expect(toErrorResponse(new Error('boom'))).toEqual({ status: 500, code: 'INTERNAL' });
  });
});
