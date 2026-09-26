'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatContentProps {
  children: string;
}

export default function ChatContent({ children }: ChatContentProps) {
  return (
    <div className="chat-content">
      <ReactMarkdown remarkPlugins={[remarkGfm]} disallowedElements={['br']}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
