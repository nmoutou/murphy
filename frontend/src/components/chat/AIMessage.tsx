'use client';

import ChatBubble from './ChatBubble';
import ChatContent from './ChatContent';
import SourcesList from './SourcesList';
import { getMessageText } from '@/lib/messageText';
import type { AppUIMessage } from '@murphy/contract/messages';

type Props = {
  message: AppUIMessage;
};

export default function AIMessage({ message }: Props) {
  const textContent = getMessageText(message);
  const chunks = message.parts.flatMap((part) => (part.type === 'data-document' ? [part.data] : []));

  return (
    <ChatBubble variant="agent">
      <div className="chat-layout">
        {textContent.trim() ? (
          <ChatContent>{textContent}</ChatContent>
        ) : (
          <span className="animate-pulse opacity-60">…</span>
        )}
      </div>

      {chunks.length > 0 && <SourcesList chunks={chunks} />}
    </ChatBubble>
  );
}
