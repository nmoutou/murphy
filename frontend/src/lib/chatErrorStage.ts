import type { ChatErrorStage } from '@murphy/contract/errors';
import { parseChatError } from '@murphy/contract/errors';

/** Raised by the transport when the socket fails, or closes before the end of the answer */
export const CONNECTION_ERROR_MESSAGE =
  'The chat WebSocket failed or closed before the end of the answer';

/** `connection` = the backend could not be reached, or dropped the answer */
export type DisplayedErrorStage = ChatErrorStage | 'connection';

/** The stage to show for a failed chat: the one the backend names (ADR-041), else `internal` */
export function readErrorStage(error: Error): DisplayedErrorStage {
  if (error.message === CONNECTION_ERROR_MESSAGE) return 'connection';
  return parseChatError(error.message)?.stage ?? 'internal';
}
