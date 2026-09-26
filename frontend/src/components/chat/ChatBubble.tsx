'use client';

import React from 'react';
import { useTheme } from '@/components/providers/ThemeProvider';

interface ChatBubbleProps {
  variant: 'user' | 'agent';
  children: React.ReactNode;
  className?: string;
}

export default function ChatBubble({ variant, children, className = '' }: ChatBubbleProps) {
  const theme = useTheme();

  const colorMap = {
    user: { bg: theme.colors.secondary, text: theme.colors.tertiary },
    agent: { bg: theme.colors.quaternary, text: theme.colors.secondary },
  };

  const colors = colorMap[variant];

  return (
    <div className={`message-container message-container-${variant}`}>
      <div 
        className={`chat-bubble chat-bubble-${variant} ${className}`}
        style={{ backgroundColor: colors.bg, color: colors.text }}
      >
        {children}
      </div>
    </div>
  );
}
