'use client';

import { useTheme } from '@/components/providers/ThemeProvider';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatContentProps {
  children: React.ReactNode;
  className?: string;
}

export default function ChatContent({ children, className = '' }: ChatContentProps) {
  const theme = useTheme();
  const isString = typeof children === 'string' || (Array.isArray(children) && children.every(c => typeof c === 'string'));

  return (
    <div className={`chat-content ${className}`}>
      {isString ? <ReactMarkdown remarkPlugins={[remarkGfm]} disallowedElements={['br']}>
        {String(children)}
      </ReactMarkdown> : children}
    </div>
  );
}
