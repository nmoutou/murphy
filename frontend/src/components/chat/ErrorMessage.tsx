'use client';

import ChatBubble from './ChatBubble';
import ChatContent from './ChatContent';
import AnimatedIcon from '@/components/icons/AnimatedIcon';

interface ErrorMessageProps {
  message: string;
}

export default function ErrorMessage({ message }: ErrorMessageProps) {
  const content = message.replace('❌ ', '');

  return (
    <ChatBubble variant="error">
      <div className="chat-layout">
        <AnimatedIcon icon="error" alt="Erreur" size={24} />
        <ChatContent>{content}</ChatContent>
      </div>
    </ChatBubble>
  );
}