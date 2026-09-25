'use client';

import ChatBubble from './ChatBubble';
import ChatContent from './ChatContent';
import SourcesList from './SourcesList';
import AnimatedButtonIcon from '@/components/icons/AnimatedButtonIcon';
import type { AppUIMessage, DocumentChunk } from '@murphy/contract/messages';

type Props = {
  message: AppUIMessage;
  onCopy?: (content: string) => void;
  onSourceClick?: (chunk: DocumentChunk) => void;
};

export default function AIMessage({ message, onCopy, onSourceClick }: Props) {
  const textContent = Array.isArray(message.parts)
    ? message.parts
        .filter((part) => part.type === 'text')
        .map((part: any) => part.text as string)
        .join('')
    : '';

  const chunks: DocumentChunk[] = Array.isArray(message.parts)
    ? message.parts
        .filter((part) => part.type === 'data-document')
        .map((part: any) => part.data as DocumentChunk)
    : [];

  const handleCopy = () => {
    navigator.clipboard.writeText(textContent);
    onCopy?.(textContent);
  };

  return (
    <ChatBubble variant="agent">
      <div className="chat-layout">
        {textContent.trim() ? (
          <ChatContent>{textContent}</ChatContent>
        ) : (
          <span className="animate-pulse opacity-60">…</span>
        )}

        {onCopy && textContent.trim() && (
          <AnimatedButtonIcon
            icon="edit"
            alt="Copier"
            size={16}
            onClick={handleCopy}
          />
        )}
      </div>

      {chunks.length > 0 && (
        <SourcesList chunks={chunks} onChunkClick={onSourceClick} />
      )}
    </ChatBubble>
  );
}
