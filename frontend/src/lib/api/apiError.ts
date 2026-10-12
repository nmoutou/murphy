import type { ApiErrorCode } from '@murphy/contract/errors';
import { apiErrorCodeSchema } from '@murphy/contract/errors';

/** `NETWORK` : le backend n'a pas répondu, aucun code ne vient de lui */
export type DisplayedErrorCode = ApiErrorCode | 'NETWORK';

export class ApiError extends Error {
  constructor(
    readonly code: DisplayedErrorCode,
    detail: string,
  ) {
    super(`${code}: ${detail}`);
    this.name = 'ApiError';
  }
}

/** Un flux d'explication interrompu porte le code seul, comme message de son erreur */
const readStreamErrorCode = (error: unknown): ApiErrorCode | undefined => {
  const parsed = apiErrorCodeSchema.safeParse(error instanceof Error ? error.message : undefined);
  return parsed.success ? parsed.data : undefined;
};

/** Le détail part dans la console ; l'utilisateur ne voit que le code */
export const reportApiError = (error: unknown): DisplayedErrorCode => {
  console.error('API request failed:', error);
  if (error instanceof ApiError) return error.code;
  return readStreamErrorCode(error) ?? 'INTERNAL';
};
