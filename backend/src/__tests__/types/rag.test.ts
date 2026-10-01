import type { RagFailure } from '../../types/rag';
import { RagError, toChatError, toRagError } from '../../types/rag';

const SEARCH_FAILURE: RagFailure = { stage: 'retrieval', code: 'SEARCH_FAILED', operation: 'search Qdrant' };

/** Une erreur du type donné, telle que la lèverait une bibliothèque cliente */
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

describe('toChatError', () => {
  it('keeps the stage and the code of a RagError, not its message', () => {
    const ragError = new RagError('retrieval', 'SEARCH_FAILED', 'Failed to search Qdrant: connect ECONNREFUSED');

    expect(toChatError(ragError)).toEqual({ stage: 'retrieval', code: 'SEARCH_FAILED' });
  });

  it.each([new Error('boom'), 'a thrown string', undefined])('turns any other failure (%p) into an internal one', (error) => {
    expect(toChatError(error)).toEqual({ stage: 'internal', code: 'INTERNAL' });
  });
});
