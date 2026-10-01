/**
 * Contrat d'erreur entre backend et frontend (ADR-041) : un échec porte l'étape fautive
 * et un code, jamais le message brut. Il voyage sérialisé dans l'`errorText` de la part
 * `error` du flux.
 */

import { z } from 'zod';

/** `request` = la requête elle-même (quota, validation, question vide) */
export const CHAT_ERROR_STAGES = ['request', 'embedding', 'retrieval', 'llm', 'internal'] as const;

export const chatErrorSchema = z.object({
  stage: z.enum(CHAT_ERROR_STAGES),
  code: z.string(),
});

export type ChatError = z.infer<typeof chatErrorSchema>;
export type ChatErrorStage = ChatError['stage'];

/** L'`errorText` d'une part `error` */
export const serializeChatError = (error: ChatError): string => JSON.stringify(error);

/** `undefined` si le texte n'est pas un `ChatError` sérialisé */
export const parseChatError = (errorText: string): ChatError | undefined => {
  let candidate: unknown;
  try {
    candidate = JSON.parse(errorText);
  } catch {
    return undefined;
  }
  const parsed = chatErrorSchema.safeParse(candidate);
  return parsed.success ? parsed.data : undefined;
};
