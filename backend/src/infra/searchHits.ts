/**
 * Vérifie les résultats d'OpenSearch contre le contrat de service (ADR-015), avant que
 * le pipeline ne s'en serve.
 */

import { z } from 'zod';
import { documentTypeSchema } from '@murphy/contract/messages';
import type { SearchHit } from '../types/rag';
import { contractViolation } from '../types/rag';
import { LEXICAL_INNER_HITS, VECTOR_INNER_HITS } from './hybridQuery';

const passageRefSchema = z
  .object({
    chunk_id: z.string().min(1),
    char_start: z.number().int(),
    char_end: z.number().int(),
  })
  .transform(({ chunk_id, char_start, char_end }) => ({ chunkId: chunk_id, charStart: char_start, charEnd: char_end }));

/** Le `_source` d'un `inner_hit` imbriqué est le passage lui-même */
const innerHitsSchema = z
  .object({ hits: z.object({ hits: z.array(z.object({ _source: passageRefSchema })) }) })
  .transform(({ hits }) => hits.hits.map((hit) => hit._source));

/** Un document trouvé par une seule sous-requête n'a pas les `inner_hits` des autres */
const searchHitSchema = z
  .object({
    _source: z.object({
      identifier: z.string().min(1),
      document_type: documentTypeSchema,
      nature: z.string().nullish(),
      passages: z.array(passageRefSchema),
    }),
    inner_hits: z
      .object({ [LEXICAL_INNER_HITS]: innerHitsSchema.optional(), [VECTOR_INNER_HITS]: innerHitsSchema.optional() })
      .optional(),
  })
  .transform(({ _source, inner_hits }): SearchHit => ({
    identifier: _source.identifier,
    documentType: _source.document_type,
    nature: _source.nature ?? undefined,
    lexicalPassages: inner_hits?.[LEXICAL_INNER_HITS] ?? [],
    vectorPassages: inner_hits?.[VECTOR_INNER_HITS] ?? [],
    allPassages: _source.passages,
  }));

const readId = (hit: unknown): string => {
  const id: unknown = typeof hit === 'object' && hit !== null ? Reflect.get(hit, '_id') : undefined;
  return typeof id === 'string' ? id : '<unknown>';
};

/**
 * @throws RagError `CONTRACT_VIOLATION` nommant le document si un champ manque ou a un
 * mauvais type
 */
export const toSearchHit = (hit: unknown): SearchHit => {
  const parsed = searchHitSchema.safeParse(hit);
  if (!parsed.success) {
    const fields = parsed.error.issues.map((issue) => issue.path.join('.')).join(', ');
    throw contractViolation(`OpenSearch document ${readId(hit)} has invalid fields: ${fields}`);
  }
  return parsed.data;
};
