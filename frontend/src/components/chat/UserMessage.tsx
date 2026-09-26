'use client';

import ChatBubble from './ChatBubble';
import ChatContent from './ChatContent';
import { getMessageText } from '@/lib/messageText';
import type { AppUIMessage } from '@murphy/contract/messages';

type Props = {
  message: AppUIMessage;
};

export default function UserMessage({ message }: Props) {
  return (
    <ChatBubble variant="user">
      <div className="chat-layout">
        <ChatContent>{getMessageText(message)}</ChatContent>
      </div>
    </ChatBubble>
  );
}
