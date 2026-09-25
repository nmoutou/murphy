'use client';

import ChatBubble from './ChatBubble';
import ChatContent from './ChatContent';
import type { AppUIMessage } from '@murphy/contract/messages';

type Props = {
  message: AppUIMessage;
};

export default function UserMessage({ message }: Props) {
  const textContent = Array.isArray(message.parts)
    ? message.parts
        .filter((part) => part.type === 'text')
        .map((part: any) => part.text as string)
        .join('')
    : '';

  return (
    <ChatBubble variant="user">
      <div className="chat-layout">
        <ChatContent>{textContent}</ChatContent>
      </div>
    </ChatBubble>
  );
}
