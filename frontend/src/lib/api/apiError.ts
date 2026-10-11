import type { SearchErrorCode } from '@murphy/contract/search';

/** `NETWORK` : le backend n'a pas répondu, aucun code ne vient de lui */
export type DisplayedErrorCode = SearchErrorCode | 'NETWORK';

export class ApiError extends Error {
  constructor(
    readonly code: DisplayedErrorCode,
    detail: string,
  ) {
    super(`${code}: ${detail}`);
    this.name = 'ApiError';
  }
}

/** Le détail part dans la console ; l'utilisateur ne voit que le code */
export const reportApiError = (error: unknown): DisplayedErrorCode => {
  console.error('API request failed:', error);
  return error instanceof ApiError ? error.code : 'INTERNAL';
};
