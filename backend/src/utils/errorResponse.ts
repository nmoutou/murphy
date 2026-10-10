import type { SearchErrorCode } from '@murphy/contract/search';
import { searchErrorCodeSchema } from '@murphy/contract/search';
import { RagError } from '../types/rag';
import { HTTP_STATUS } from './httpStatus';

export interface ErrorResponse {
  readonly status: number;
  readonly code: SearchErrorCode;
}

const INTERNAL_ERROR_RESPONSE: ErrorResponse = { status: HTTP_STATUS.INTERNAL_SERVER_ERROR, code: 'INTERNAL' };

/** Un service en aval qui échoue est un 502, un 504 s'il ne répond pas à temps (ADR-031 §4) */
const STATUS_BY_RAG_ERROR_CODE: Readonly<Partial<Record<SearchErrorCode, number>>> = {
  PAGE_OUT_OF_RANGE: HTTP_STATUS.BAD_REQUEST,
  DOCUMENT_NOT_FOUND: HTTP_STATUS.NOT_FOUND,
  EMBEDDING_FAILED: HTTP_STATUS.BAD_GATEWAY,
  SEARCH_FAILED: HTTP_STATUS.BAD_GATEWAY,
  DB_FETCH_FAILED: HTTP_STATUS.BAD_GATEWAY,
  TIMEOUT: HTTP_STATUS.GATEWAY_TIMEOUT,
  CONTRACT_VIOLATION: HTTP_STATUS.INTERNAL_SERVER_ERROR,
};

/** Ce que le client apprend d'un échec : un statut et un code, jamais le message brut */
export const toErrorResponse = (error: unknown): ErrorResponse => {
  if (!(error instanceof RagError)) return INTERNAL_ERROR_RESPONSE;
  const parsed = searchErrorCodeSchema.safeParse(error.code);
  const status = parsed.success ? STATUS_BY_RAG_ERROR_CODE[parsed.data] : undefined;
  return parsed.success && status !== undefined ? { status, code: parsed.data } : INTERNAL_ERROR_RESPONSE;
};
