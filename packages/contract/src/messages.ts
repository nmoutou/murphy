/**
 * Contrat du flux entre backend et frontend : le backend écrit ces parts, le frontend
 * les valide avec ces mêmes schémas, et tous deux compilent contre ces types. Un
 * changement casse les deux côtés à la fois.
 */

import type { UIMessage } from 'ai';
import { z } from 'zod';

/** La forme d'un document, identique dans tous les stores de l'ingestion (ADR-046) */
export const documentTypeSchema = z.enum(['article', 'section', 'texte', 'decision']);

/**
 * Un passage retrouvé (ADR-039) : son texte est `content.slice(highlightStart,
 * highlightEnd)` du `ParentDocument` de même `identifier`. `title`, `documentType` et
 * `nature` répètent ceux du parent tant que le frontend ne lit pas `ParentDocument`.
 */
export const documentChunkSchema = z.object({
  chunkId: z.string(),
  identifier: z.string(),
  /** Offsets UTF-16 dans le `content` du parent, comme les compte JavaScript */
  highlightStart: z.number().int().nonnegative(),
  highlightEnd: z.number().int().nonnegative(),
  score: z.number(),
  title: z.string().optional(),
  documentType: documentTypeSchema,
  /** La nature juridique (`LOI`, `ARRET`, `QPC`…), quand la source en donne une utile */
  nature: z.string().optional(),
});

/** Le document entier d'un passage, envoyé une fois par réponse, avant ses passages */
export const parentDocumentSchema = z.object({
  identifier: z.string(),
  title: z.string(),
  documentType: documentTypeSchema,
  nature: z.string().optional(),
  content: z.string(),
});

/** Latence de chaque étape du pipeline, en millisecondes */
export const ragTimingSchema = z.object({
  embeddingMs: z.number(),
  retrievalMs: z.number(),
  docFetchMs: z.number().optional(),
  totalMs: z.number(),
  llmMs: z.number().optional(),
});

export const appMessageMetadataSchema = z.object({
  ragTiming: ragTimingSchema.optional(),
});

/** Clé = nom de la part : `document` voyage en part `data-document` */
export const appDataPartSchemas = {
  document: documentChunkSchema,
  parentDocument: parentDocumentSchema,
};

export type DocumentType = z.infer<typeof documentTypeSchema>;
export type DocumentChunk = z.infer<typeof documentChunkSchema>;
export type ParentDocument = z.infer<typeof parentDocumentSchema>;
export type RagTiming = z.infer<typeof ragTimingSchema>;
export type AppMessageMetadata = z.infer<typeof appMessageMetadataSchema>;

export type AppUIMessage = UIMessage<
  AppMessageMetadata,
  { document: DocumentChunk; parentDocument: ParentDocument }
>;
