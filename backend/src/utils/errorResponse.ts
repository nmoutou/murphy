import type { ApiErrorCode } from '@murphy/contract/errors';
import { apiErrorCodeSchema } from '@murphy/contract/errors';
import { RagError } from '../types/rag';
import { HTTP_STATUS } from './httpStatus';

export interface ErrorResponse {
  readonly status: number;
  readonly code: ApiErrorCode;
}

const INTERNAL_ERROR_RESPONSE: ErrorResponse = { status: HTTP_STATUS.INTERNAL_SERVER_ERROR, code: 'INTERNAL' };

/** Un service en aval qui échoue est un 502, un 504 s'il ne répond pas à temps (ADR-030 §4) */
const STATUS_BY_RAG_ERROR_CODE: Readonly<Partial<Record<ApiErrorCode, number>>> = {
  PAGE_OUT_OF_RANGE: HTTP_STATUS.BAD_REQUEST,
  CONTEXT_TOO_LARGE: HTTP_STATUS.BAD_REQUEST,
  DOCUMENT_NOT_FOUND: HTTP_STATUS.NOT_FOUND,
  EMBEDDING_FAILED: HTTP_STATUS.BAD_GATEWAY,
  SEARCH_FAILED: HTTP_STATUS.BAD_GATEWAY,
  DB_FETCH_FAILED: HTTP_STATUS.BAD_GATEWAY,
  LLM_FAILED: HTTP_STATUS.BAD_GATEWAY,
  TIMEOUT: HTTP_STATUS.GATEWAY_TIMEOUT,
  CONTRACT_VIOLATION: HTTP_STATUS.INTERNAL_SERVER_ERROR,
};

/** Ce que le client apprend d'un échec : un statut et un code, jamais le message brut */
export const toErrorResponse = (error: unknown): ErrorResponse => {
  if (!(error instanceof RagError)) return INTERNAL_ERROR_RESPONSE;
  const parsed = apiErrorCodeSchema.safeParse(error.code);
  const status = parsed.success ? STATUS_BY_RAG_ERROR_CODE[parsed.data] : undefined;
  return parsed.success && status !== undefined ? { status, code: parsed.data } : INTERNAL_ERROR_RESPONSE;
};
