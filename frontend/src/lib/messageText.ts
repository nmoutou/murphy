import type { AppUIMessage } from '@murphy/contract/messages';

/** The concatenated text parts of a message, in order */
export function getMessageText(message: AppUIMessage): string {
  return message.parts.map((part) => (part.type === 'text' ? part.text : '')).join('');
}
