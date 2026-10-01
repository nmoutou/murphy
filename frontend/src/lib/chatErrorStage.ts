import type { ChatErrorStage } from '@murphy/contract/errors';
import { parseChatError } from '@murphy/contract/errors';

/** Levée par le transport quand la socket échoue ou ferme avant la fin de la réponse */
export const CONNECTION_ERROR_MESSAGE =
  'The chat WebSocket failed or closed before the end of the answer';

/** `connection` = backend injoignable, ou réponse abandonnée */
export type DisplayedErrorStage = ChatErrorStage | 'connection';

/** L'étape nommée par le backend (ADR-041), sinon `internal` */
export function readErrorStage(error: Error): DisplayedErrorStage {
  if (error.message === CONNECTION_ERROR_MESSAGE) return 'connection';
  return parseChatError(error.message)?.stage ?? 'internal';
}
