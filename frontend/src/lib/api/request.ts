import type { ApiErrorCode } from '@murphy/contract/errors';
import { apiErrorCodeSchema } from '@murphy/contract/errors';
import { ApiError } from './apiError';
import { buildApiUrl } from './apiUrl';

const UNREADABLE_ERROR_CODE: ApiErrorCode = 'INTERNAL';

type ParseResult<T> =
  | { readonly success: true; readonly data: T }
  | { readonly success: false; readonly error: unknown };

/** Ce que le frontend utilise d'un schéma zod, sans dépendre de zod lui-même */
export interface ResponseSchema<T> {
  safeParse(input: unknown): ParseResult<T>;
}

const sendRequest = async (path: string, init: RequestInit): Promise<Response> => {
  const url = buildApiUrl(path);
  try {
    return await fetch(url, init);
  } catch (error) {
    if (init.signal?.aborted) throw error;
    throw new ApiError('NETWORK', `${init.method ?? 'GET'} ${path}: ${String(error)}`);
  }
};

export const readJson = async (response: Response): Promise<unknown> => {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
};

/** L'enveloppe `{ status: { code, message }, data?, meta }` : sur un échec, `status.message` est le code */
export const readErrorCode = (body: unknown): ApiErrorCode => {
  const status =
    typeof body === 'object' && body !== null && 'status' in body ? body.status : undefined;
  const message =
    typeof status === 'object' && status !== null && 'message' in status
      ? status.message
      : undefined;
  const parsed = apiErrorCodeSchema.safeParse(message);
  return parsed.success ? parsed.data : UNREADABLE_ERROR_CODE;
};

const readData = (body: unknown): unknown =>
  typeof body === 'object' && body !== null && 'data' in body ? body.data : undefined;

/**
 * Un appel au backend, son `data` validé par le schéma
 * @throws ApiError : `NETWORK` sans réponse, le code de l'API sur un échec, `INTERNAL` sur une
 * réponse illisible ; l'erreur d'origine si la requête est annulée
 */
export const requestApi = async <T>(
  path: string,
  init: RequestInit,
  schema: ResponseSchema<T>,
): Promise<T> => {
  const response = await sendRequest(path, init);
  const body = await readJson(response);
  if (!response.ok) {
    throw new ApiError(readErrorCode(body), `HTTP ${response.status} on ${path}`);
  }
  const parsed = schema.safeParse(readData(body));
  if (!parsed.success) {
    throw new ApiError(
      UNREADABLE_ERROR_CODE,
      `Invalid response on ${path}: ${String(parsed.error)}`,
    );
  }
  return parsed.data;
};
