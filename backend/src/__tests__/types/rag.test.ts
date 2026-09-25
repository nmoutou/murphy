/**
 * RAG Error Tests
 * `toRagError`, the one translation of an infrastructure failure
 */

import type { RagFailure } from '../../types/rag';
import { toRagError } from '../../types/rag';

const SEARCH_FAILURE: RagFailure = { stage: 'retrieval', code: 'SEARCH_FAILED', operation: 'search Qdrant' };

/** An error of the given type, as a client library would throw it */
const errorNamed = (name: string, message: string): Error => Object.assign(new Error(message), { name });

describe('toRagError', () => {
  it('keeps the failure code and says which operation failed', () => {
    const ragError = toRagError(SEARCH_FAILURE, new Error('connect ECONNREFUSED'));

    expect(ragError).toMatchObject({
      name: 'RagError',
      stage: 'retrieval',
      code: 'SEARCH_FAILED',
      message: 'Failed to search Qdrant: connect ECONNREFUSED',
    });
  });

  it.each(['TimeoutError', 'QdrantClientTimeoutError', 'MongoNetworkTimeoutError'])(
    'classifies a %s as a timeout',
    (name) => {
      expect(toRagError(SEARCH_FAILURE, errorNamed(name, 'too slow')).code).toBe('TIMEOUT');
    },
  );

  it('does not read the message to guess a timeout', () => {
    expect(toRagError(SEARCH_FAILURE, new Error('upstream timeout')).code).toBe('SEARCH_FAILED');
  });

  it('accepts a thrown value that is not an Error', () => {
    expect(toRagError(SEARCH_FAILURE, 'boom').message).toBe('Failed to search Qdrant: boom');
  });
});
