import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { SearchRequest, SearchResponse } from '@murphy/contract/search';
import { ApiError } from '@/lib/api/apiError';
import { searchDocuments } from '@/lib/api/search';
import { useErrorStore } from '@/stores/errorStore';
import { useSearchStore } from '@/stores/searchStore';

vi.mock('@/lib/api/search', () => ({ searchDocuments: vi.fn() }));

const QUESTION = 'Quel délai de prescription ?';

const responseFor = ({ page, pageSize = 10 }: SearchRequest): SearchResponse => ({
  page,
  pageCount: Math.ceil(100 / pageSize),
  pageSize,
  pageSizes: [10, 25, 50],
  results: [
    { identifier: `doc-${page}`, title: 'Article 2224', documentType: 'article', passages: [] },
  ],
});

const searchMock = vi.mocked(searchDocuments);

const lastRequest = (): SearchRequest | undefined => searchMock.mock.lastCall?.[0];

beforeEach(() => {
  searchMock.mockReset();
  searchMock.mockImplementation((request) => Promise.resolve(responseFor(request)));
  useSearchStore.setState(useSearchStore.getInitialState(), true);
  useErrorStore.setState(useErrorStore.getInitialState(), true);
});

describe('searchStore', () => {
  it('starts idle, before any search', () => {
    expect(useSearchStore.getState()).toMatchObject({ status: 'idle', question: '' });
  });

  it('searches the first page, then keeps the response and its page size', async () => {
    await useSearchStore.getState().submit(QUESTION);

    expect(lastRequest()).toEqual({ question: QUESTION, page: 1, pageSize: undefined });
    expect(useSearchStore.getState()).toMatchObject({
      status: 'success',
      question: QUESTION,
      page: 1,
      pageSize: 10,
      response: responseFor({ question: QUESTION, page: 1 }),
    });
  });

  it('is loading until the response arrives', () => {
    searchMock.mockReturnValue(new Promise(() => {}));

    void useSearchStore.getState().submit(QUESTION);

    expect(useSearchStore.getState().status).toBe('loading');
  });

  it('empties the list, keeps the question and shows the error code', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    await useSearchStore.getState().submit(QUESTION);
    searchMock.mockRejectedValue(new ApiError('SEARCH_FAILED', 'HTTP 502 on /search'));

    await useSearchStore.getState().goToPage(2);

    expect(useSearchStore.getState()).toMatchObject({ status: 'error', question: QUESTION });
    expect(useSearchStore.getState().response).toBeUndefined();
    expect(useErrorStore.getState().errorCode).toBe('SEARCH_FAILED');
  });

  it('shows INTERNAL for an error that is not an ApiError', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    searchMock.mockRejectedValue(new Error('NEXT_PUBLIC_API_URL is invalid'));

    await useSearchStore.getState().submit(QUESTION);

    expect(useErrorStore.getState().errorCode).toBe('INTERNAL');
  });

  it('ignores a late response, and aborts its request', async () => {
    let resolveFirst: (response: SearchResponse) => void = () => {};
    searchMock.mockImplementationOnce(() => new Promise((resolve) => (resolveFirst = resolve)));
    const first = useSearchStore.getState().submit('Première question');
    const firstSignal = searchMock.mock.calls[0]?.[1];

    await useSearchStore.getState().submit(QUESTION);
    resolveFirst(responseFor({ question: 'Première question', page: 7 }));
    await first;

    expect(firstSignal?.aborted).toBe(true);
    expect(useSearchStore.getState()).toMatchObject({ status: 'success', question: QUESTION });
    expect(useSearchStore.getState().response?.page).toBe(1);
  });

  it('ignores the failure of an aborted request', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    searchMock.mockImplementationOnce((_request, signal) => {
      return new Promise((_resolve, reject) => {
        signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
      });
    });
    const first = useSearchStore.getState().submit('Première question');

    await useSearchStore.getState().submit(QUESTION);
    await first;

    expect(useSearchStore.getState().status).toBe('success');
    expect(useErrorStore.getState().errorCode).toBeUndefined();
    expect(consoleError).not.toHaveBeenCalled();
  });

  it('keeps the question and the page size when changing page', async () => {
    await useSearchStore.getState().submit(QUESTION);
    await useSearchStore.getState().setPageSize(25);

    await useSearchStore.getState().goToPage(3);

    expect(lastRequest()).toEqual({ question: QUESTION, page: 3, pageSize: 25 });
  });

  it('searches again from the first page when the page size changes', async () => {
    await useSearchStore.getState().submit(QUESTION);
    await useSearchStore.getState().goToPage(4);

    await useSearchStore.getState().setPageSize(50);

    expect(lastRequest()).toEqual({ question: QUESTION, page: 1, pageSize: 50 });
    expect(useSearchStore.getState()).toMatchObject({ page: 1, pageSize: 50 });
  });

  it('keeps the chosen page size for a new question', async () => {
    await useSearchStore.getState().submit('Première question');
    await useSearchStore.getState().setPageSize(25);

    await useSearchStore.getState().submit(QUESTION);

    expect(lastRequest()).toEqual({ question: QUESTION, page: 1, pageSize: 25 });
  });
});
