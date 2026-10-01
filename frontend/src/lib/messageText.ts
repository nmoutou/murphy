import type { AppUIMessage } from '@murphy/contract/messages';

export function getMessageText(message: AppUIMessage): string {
  return message.parts.map((part) => (part.type === 'text' ? part.text : '')).join('');
}
