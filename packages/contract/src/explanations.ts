/**
 * Contrat de `POST /api/v1/explanations` (ADR-033 §10) : la sélection et le segment
 * courant de la conversation. La réponse est un flux SSE de l'AI SDK, pas une enveloppe.
 */

import { z } from 'zod';

export const explanationRoleSchema = z.enum(['user', 'assistant']);

export const explanationMessageSchema = z.object({
  role: explanationRoleSchema,
  content: z.string().min(1),
});

const hasNoDuplicate = (identifiers: readonly string[]): boolean =>
  new Set(identifiers).size === identifiers.length;

export const explanationRequestSchema = z.object({
  /** Les identifiants dans l'ordre de la sélection : `[n]` désigne le n-ième */
  selection: z
    .array(z.string().min(1))
    .min(1)
    .refine(hasNoDuplicate, { message: 'A document appears twice in the selection' }),
  /** Le segment courant : les messages depuis le dernier changement de sélection */
  messages: z
    .array(explanationMessageSchema)
    .min(1)
    .refine((messages) => messages[messages.length - 1]?.role === 'user', {
      message: 'The last message must come from the user',
    }),
});

export type ExplanationRole = z.infer<typeof explanationRoleSchema>;
export type ExplanationMessage = z.infer<typeof explanationMessageSchema>;
export type ExplanationRequest = z.infer<typeof explanationRequestSchema>;
