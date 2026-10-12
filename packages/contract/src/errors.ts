/**
 * Les codes d'erreur de l'API (ADR-030 §4, ADR-033 §11) : sur un échec, `status.message`
 * de l'enveloppe, jamais le message brut. Un flux d'explication interrompu par une erreur
 * porte l'un d'eux dans son événement d'erreur.
 */

import { z } from 'zod';

export const API_ERROR_CODES = [
  'VALIDATION_ERROR',
  'INVALID_JSON',
  'INVALID_REQUEST_BODY',
  'PAGE_OUT_OF_RANGE',
  'CONTEXT_TOO_LARGE',
  'DOCUMENT_NOT_FOUND',
  'NOT_FOUND',
  'PAYLOAD_TOO_LARGE',
  'SEARCH_RATE_LIMIT_EXCEEDED',
  'EXPLANATION_RATE_LIMIT_EXCEEDED',
  'EXPLANATION_QUOTA_EXCEEDED',
  'RATE_LIMIT_EXCEEDED',
  'EMBEDDING_FAILED',
  'SEARCH_FAILED',
  'DB_FETCH_FAILED',
  'LLM_FAILED',
  'TIMEOUT',
  'CONTRACT_VIOLATION',
  'INTERNAL',
] as const;

export const apiErrorCodeSchema = z.enum(API_ERROR_CODES);

export type ApiErrorCode = z.infer<typeof apiErrorCodeSchema>;
