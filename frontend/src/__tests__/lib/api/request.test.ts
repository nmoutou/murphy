import { describe, expect, it, vi } from 'vitest';
import { searchResponseSchema } from '@murphy/contract/search';
import type { SearchResponse } from '@murphy/contract/search';
import { ApiError } from '@/lib/api/apiError';
import { fetchDocument } from '@/lib/api/documents';
import { requestApi } from '@/lib/api/request';
import { searchDocuments } from '@/lib/api/search';

const SEARCH_RESPONSE: SearchResponse = {
  page: 1,
  pageCount: 10,
  pageSize: 10,
  pageSizes: [10, 25, 50],
  contextBudget: 100_000,
  results: [],
};

const envelope = (message: string, data?: unknown) => ({
  status: { code: 200, message },
  ...(data === undefined ? {} : { data }),
  meta: { timestamp: '2026-10-11T00:00:00.000Z', traceId: 'trace' },
});

const stubFetch = (response: Response) => {
  const fetchMock = vi.fn(() => Promise.resolve(response));
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
};

const stubFailedFetch = (error: unknown) =>
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.reject(error)),
  );

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

const requestSearch = () => requestApi('/search', { method: 'POST' }, searchResponseSchema);

const rejectionOf = async (promise: Promise<unknown>): Promise<unknown> => {
  try {
    await promise;
  } catch (error) {
    return error;
  }
  throw new Error('The request was expected to fail');
};

describe('requestApi', () => {
  it('returns the data of the envelope, validated by the schema', async () => {
    stubFetch(jsonResponse(envelope('OK', SEARCH_RESPONSE)));

    await expect(requestSearch()).resolves.toEqual(SEARCH_RESPONSE);
  });

  it('turns a failed fetch into NETWORK', async () => {
    stubFailedFetch(new TypeError('Failed to fetch'));

    const error = await rejectionOf(requestSearch());

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toHaveProperty('code', 'NETWORK');
  });

  it('rethrows the original error of an aborted request', async () => {
    const abort = new DOMException('Aborted', 'AbortError');
    stubFailedFetch(abort);
    const controller = new AbortController();
    controller.abort();

    const error = await rejectionOf(
      requestApi('/search', { signal: controller.signal }, searchResponseSchema),
    );

    expect(error).toBe(abort);
  });

  it('carries the code of a failure envelope', async () => {
    stubFetch(jsonResponse(envelope('PAGE_OUT_OF_RANGE'), 400));

    await expect(requestSearch()).rejects.toHaveProperty('code', 'PAGE_OUT_OF_RANGE');
  });

  it.each([
    ['an unknown code', jsonResponse(envelope('TEAPOT'), 418)],
    ['a body without status', jsonResponse({ error: 'Bad gateway' }, 502)],
    ['a body that is not JSON', new Response('<html>Bad gateway</html>', { status: 502 })],
  ])('answers INTERNAL to a failure with %s', async (_case, response) => {
    stubFetch(response);

    await expect(requestSearch()).rejects.toHaveProperty('code', 'INTERNAL');
  });

  it.each([
    ['data that breaks the schema', jsonResponse(envelope('OK', { page: 'one' }))],
    ['no data', jsonResponse(envelope('OK'))],
    ['a body that is not JSON', new Response('OK', { status: 200 })],
  ])('answers INTERNAL to a success with %s', async (_case, response) => {
    stubFetch(response);

    await expect(requestSearch()).rejects.toHaveProperty('code', 'INTERNAL');
  });
});

describe('searchDocuments', () => {
  it('posts the request as JSON to the search route of NEXT_PUBLIC_API_URL', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'https://api.murphy.test');
    const fetchMock = stubFetch(jsonResponse(envelope('OK', SEARCH_RESPONSE)));
    const request = { question: 'Quel délai de prescription ?', page: 2, pageSize: 25 };

    await searchDocuments(request, new AbortController().signal);

    expect(fetchMock).toHaveBeenCalledExactlyOnceWith(
      'https://api.murphy.test/api/v1/search',
      expect.objectContaining({ method: 'POST', body: JSON.stringify(request) }),
    );
  });

  it('defaults to the local backend', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_URL', '');
    const fetchMock = stubFetch(jsonResponse(envelope('OK', SEARCH_RESPONSE)));

    await searchDocuments({ question: 'q', page: 1 }, new AbortController().signal);

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:5000/api/v1/search',
      expect.anything(),
    );
  });
});

describe('fetchDocument', () => {
  it('gets the document route, the identifier encoded', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'https://api.murphy.test');
    const document = {
      identifier: 'JURI/TEXT 1',
      title: 'Arrêt',
      content: 'Attendu que…',
      contentLength: 12,
    };
    const fetchMock = stubFetch(jsonResponse(envelope('OK', document)));

    await expect(fetchDocument('JURI/TEXT 1', new AbortController().signal)).resolves.toEqual(
      document,
    );
    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.murphy.test/api/v1/documents/JURI%2FTEXT%201',
      expect.not.objectContaining({ method: expect.anything() }),
    );
  });
});
