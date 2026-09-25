/**
 * Chat Request Validation
 * Checks the `{ messages }` payload at the system boundary; shared by the HTTP
 * routes (`routes/chat.ts`) and the WebSocket (`routes/chatWebSocket.ts`)
 */

import type { AppUIMessage } from '../types/messages';

export interface ValidationIssue {
  readonly field: string;
  readonly message: string;
}

export type ChatRequestParseResult =
  | { readonly isValid: true; readonly messages: AppUIMessage[] }
  | { readonly isValid: false; readonly issues: ValidationIssue[] };

const MESSAGE_ROLES: ReadonlySet<unknown> = new Set(['user', 'assistant', 'system']);

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

const isTypedPart = (part: unknown): boolean => isRecord(part) && typeof part.type === 'string';

const collectMessageIssues = (message: unknown, index: number): ValidationIssue[] => {
  const field = `messages[${index}]`;
  const fields = isRecord(message) ? message : {};
  const issues: ValidationIssue[] = [];

  if (!MESSAGE_ROLES.has(fields.role)) {
    issues.push({ field: `${field}.role`, message: 'message role must be user, assistant, or system' });
  }
  if (!Array.isArray(fields.parts) || !fields.parts.every(isTypedPart)) {
    issues.push({ field: `${field}.parts`, message: 'parts must be an array of objects with a string type' });
  }
  return issues;
};

export const parseChatRequest = (body: unknown): ChatRequestParseResult => {
  const messages: unknown = isRecord(body) ? body.messages : undefined;
  if (!Array.isArray(messages) || messages.length === 0) {
    return { isValid: false, issues: [{ field: 'messages', message: 'messages must be a non-empty array' }] };
  }

  const issues = messages.flatMap(collectMessageIssues);
  if (issues.length > 0) return { isValid: false, issues };

  // Role and parts are checked above; the rest of the AI SDK message shape is
  // trusted, as `useChat` builds it
  const checkedMessages: unknown[] = messages;
  return { isValid: true, messages: checkedMessages as AppUIMessage[] };
};
