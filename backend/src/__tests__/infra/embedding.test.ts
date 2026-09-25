/**
 * Embedding Client Tests
 * The TEI call and the reading of its response, over a mocked `fetch`
 */

import { EmbeddingClient } from '../../infra/embedding';

jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

const SETTINGS = { serviceUrl: 'http://tei.test', modelName: 'test-model', timeoutMs: 1000 };
const QUESTION = 'Quel délai ?';
const EMBEDDING = [0.1, 0.2, 0.3];
const HTTP_SERVER_ERROR = 500;

const jsonResponse = (body: unknown): Response => new Response(JSON.stringify(body));

describe('EmbeddingClient.embedText', () => {
  it('posts the text to TEI and returns the first vector', async () => {
    const fetchSpy = jest.spyOn(global, 'fetch').mockResolvedValue(jsonResponse({ data: [{ embedding: EMBEDDING, index: 0 }] }));

    await expect(new EmbeddingClient(SETTINGS).embedText(QUESTION)).resolves.toEqual(EMBEDDING);
    expect(fetchSpy).toHaveBeenCalledWith(
      'http://tei.test/v1/embeddings',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ model: 'test-model', input: [QUESTION] }) }),
    );
  });

  it('fails with an embedding RagError when TEI answers an HTTP error', async () => {
    jest.spyOn(global, 'fetch').mockResolvedValue(
      new Response('down', { status: HTTP_SERVER_ERROR, statusText: 'Internal Server Error' }),
    );

    await expect(new EmbeddingClient(SETTINGS).embedText(QUESTION)).rejects.toMatchObject({
      name: 'RagError',
      stage: 'embedding',
      code: 'NETWORK',
      message: 'Failed to generate embeddings: TEI service returned 500: Internal Server Error',
    });
  });

  it.each([
    ['without vector', { data: [] }],
    ['with a vector that is not numeric', { data: [{ embedding: ['0.1'] }] }],
  ])('rejects a response %s', async (_case, body) => {
    jest.spyOn(global, 'fetch').mockResolvedValue(jsonResponse(body));

    await expect(new EmbeddingClient(SETTINGS).embedText(QUESTION)).rejects.toThrow(
      'Failed to generate embeddings: Invalid embedding response format',
    );
  });

  it('reports a timeout as such', async () => {
    jest.spyOn(global, 'fetch').mockRejectedValue(new DOMException('The operation timed out', 'TimeoutError'));

    await expect(new EmbeddingClient(SETTINGS).embedText(QUESTION)).rejects.toMatchObject({ code: 'TIMEOUT' });
  });
});
