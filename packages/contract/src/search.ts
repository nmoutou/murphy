/**
 * Contrat de l'API de recherche (ADR-031) : `POST /api/v1/search` et
 * `GET /api/v1/documents/:identifier`. Ces schémas décrivent le `data` de l'enveloppe
 * `{ status, data, meta }` ; une erreur n'a pas de `data`, son code est `status.message`.
 */

import { z } from 'zod';

export const documentTypeSchema = z.enum(['article', 'section', 'texte', 'decision']);

export const searchRequestSchema = z.object({
  question: z.string().trim().min(1),
  page: z.number().int().positive().default(1),
});

export const passageSchema = z.object({
  chunkId: z.string(),
  text: z.string(),
  /** Offsets UTF-16 dans le `content` du document, comme les compte JavaScript */
  start: z.number().int().nonnegative(),
  end: z.number().int().nonnegative(),
});

/** Sans passage correspondant, `passages` est vide : le texte se lit par `GET /documents` */
export const searchResultSchema = z.object({
  identifier: z.string(),
  title: z.string(),
  documentType: documentTypeSchema,
  /** La nature juridique (`LOI`, `ARRET`, `QPC`…), quand la source en donne une utile */
  nature: z.string().optional(),
  passages: z.array(passageSchema),
});

/** Au-delà des documents trouvés mais jusqu'à `pageCount`, `results` est vide */
export const searchResponseSchema = z.object({
  page: z.number().int().positive(),
  pageCount: z.number().int().positive(),
  results: z.array(searchResultSchema),
});

export const documentContentSchema = z.object({
  identifier: z.string(),
  title: z.string(),
  content: z.string(),
});

export const SEARCH_ERROR_CODES = [
  'VALIDATION_ERROR',
  'INVALID_JSON',
  'PAGE_OUT_OF_RANGE',
  'DOCUMENT_NOT_FOUND',
  'PAYLOAD_TOO_LARGE',
  'SEARCH_RATE_LIMIT_EXCEEDED',
  'RATE_LIMIT_EXCEEDED',
  'EMBEDDING_FAILED',
  'SEARCH_FAILED',
  'DB_FETCH_FAILED',
  'TIMEOUT',
  'CONTRACT_VIOLATION',
  'INTERNAL',
] as const;

export const searchErrorCodeSchema = z.enum(SEARCH_ERROR_CODES);

export type DocumentType = z.infer<typeof documentTypeSchema>;
export type SearchRequest = z.infer<typeof searchRequestSchema>;
export type Passage = z.infer<typeof passageSchema>;
export type SearchResult = z.infer<typeof searchResultSchema>;
export type SearchResponse = z.infer<typeof searchResponseSchema>;
export type DocumentContent = z.infer<typeof documentContentSchema>;
export type SearchErrorCode = z.infer<typeof searchErrorCodeSchema>;
