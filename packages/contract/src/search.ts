/**
 * Contrat de l'API de recherche (ADR-030) : `POST /api/v1/search` et
 * `GET /api/v1/documents/:identifier`. Ces schémas décrivent le `data` de l'enveloppe
 * `{ status, data, meta }` ; une erreur n'a pas de `data`, son code est `status.message`
 * (`@murphy/contract/errors`).
 */

import { z } from 'zod';

export const documentTypeSchema = z.enum(['article', 'section', 'texte', 'decision']);

export const searchRequestSchema = z.object({
  question: z.string().trim().min(1),
  page: z.number().int().positive().default(1),
  /** Absente : la première des `pageSizes` du serveur ; hors de cette liste : refusée */
  pageSize: z.number().int().positive().optional(),
});

/** La longueur de `content` en points de code, écrite à l'ingestion : rapportée au budget de contexte */
const contentLengthSchema = z.number().int().nonnegative();

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
  /** Absent quand la source ne donne pas de statut, comme pour une décision */
  isInForce: z.boolean().optional(),
  contentLength: contentLengthSchema,
  passages: z.array(passageSchema),
});

/** Au-delà des documents trouvés mais jusqu'à `pageCount`, `results` est vide */
export const searchResponseSchema = z.object({
  page: z.number().int().positive(),
  pageCount: z.number().int().positive(),
  pageSize: z.number().int().positive(),
  /** Les tailles de page que le serveur accepte, la première par défaut */
  pageSizes: z.array(z.number().int().positive()).min(1),
  /** Le budget de contexte du LLM, en points de code, comparé à la somme des `contentLength` */
  contextBudget: z.number().int().positive(),
  results: z.array(searchResultSchema),
});

export const documentContentSchema = z.object({
  identifier: z.string(),
  title: z.string(),
  content: z.string(),
  contentLength: contentLengthSchema,
});

export type DocumentType = z.infer<typeof documentTypeSchema>;
export type SearchRequest = z.infer<typeof searchRequestSchema>;
export type Passage = z.infer<typeof passageSchema>;
export type SearchResult = z.infer<typeof searchResultSchema>;
export type SearchResponse = z.infer<typeof searchResponseSchema>;
export type DocumentContent = z.infer<typeof documentContentSchema>;
