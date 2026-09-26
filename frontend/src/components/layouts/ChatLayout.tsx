'use client';

import { useEffect, useRef } from 'react';
import UserMessage from '@/components/chat/UserMessage';
import AIMessage from '@/components/chat/AIMessage';
import type { AppUIMessage } from '@murphy/contract/messages';

interface ChatLayoutProps {
  messages: Array<AppUIMessage>;
}

export default function ChatLayout({ messages }: ChatLayoutProps) {
  const hasHistory = messages.length > 2;

  const lastUserRef = useRef<HTMLDivElement | null>(null);
  const lastMessage = messages[messages.length - 1];

  useEffect(() => {
    if (lastMessage?.role === 'user') {
      lastUserRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [lastMessage]);

  return (
    <div
      className={`w-[70%] min-w-[310px] flex flex-col gap-4 ${hasHistory ? 'pb-[90vh]' : 'pb-0'}`}
    >
      {messages.map((message, index) => {
        const isLastUser = message.role === 'user' && index === messages.length - 1;
        const ref = isLastUser ? lastUserRef : undefined;

        // scroll-mt only acts on the scrollIntoView target: the last question
        return (
          <div key={message.id} ref={ref} className="scroll-mt-4">
            {message.role === 'user' ? (
              <UserMessage message={message} />
            ) : (
              <AIMessage message={message} />
            )}
          </div>
        );
      })}
    </div>
  );
}
