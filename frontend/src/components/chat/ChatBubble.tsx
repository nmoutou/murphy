'use client';

import React from 'react';

interface ChatBubbleProps {
  variant: 'user' | 'agent';
  children: React.ReactNode;
  className?: string;
}

export default function ChatBubble({ variant, children, className = '' }: ChatBubbleProps) {
  return (
    <div className={`message-container message-container-${variant}`}>
      <div className={`chat-bubble chat-bubble-${variant} ${className}`}>{children}</div>
    </div>
  );
}
