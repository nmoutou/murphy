import type { SearchRequest, SearchResponse } from '@murphy/contract/search';
import { searchResponseSchema } from '@murphy/contract/search';
import { requestApi } from './request';

const SEARCH_PATH = '/search';
const JSON_HEADERS = { 'Content-Type': 'application/json' };

/** La question voyage dans le corps, jamais dans l'URL */
export const searchDocuments = (
  request: SearchRequest,
  signal: AbortSignal,
): Promise<SearchResponse> =>
  requestApi(
    SEARCH_PATH,
    { method: 'POST', headers: JSON_HEADERS, body: JSON.stringify(request), signal },
    searchResponseSchema,
  );
