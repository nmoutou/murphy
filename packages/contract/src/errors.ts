/**
 * The error contract between backend and frontend (ADR-041): a failed chat carries the
 * pipeline stage at fault and a code, never the raw message. The backend serializes it
 * into the `errorText` of the stream's `error` part; the frontend reads it back to name
 * the failed stage.
 */

import { z } from 'zod';

/** `request` = the payload itself (quota, validation, empty question) */
export const CHAT_ERROR_STAGES = ['request', 'embedding', 'retrieval', 'llm', 'internal'] as const;

export const chatErrorSchema = z.object({
  stage: z.enum(CHAT_ERROR_STAGES),
  code: z.string(),
});

export type ChatError = z.infer<typeof chatErrorSchema>;
export type ChatErrorStage = ChatError['stage'];

/** The `errorText` of an `error` part */
export const serializeChatError = (error: ChatError): string => JSON.stringify(error);

/** `undefined` when the text is not a serialized `ChatError` */
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
