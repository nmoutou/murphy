import { Fragment } from 'react';
import type { ExplanationUIMessage } from '@/lib/api/explanationRequest';
import { sourcesAt, startsSegment, textOf } from '@/lib/api/explanationRequest';
import type { SelectionEntry } from '@/stores/selectionStore';
import AssistantMessage from './AssistantMessage';
import SegmentSeparator from './SegmentSeparator';
import UserMessage from './UserMessage';

interface MessageListProps {
  readonly messages: readonly ExplanationUIMessage[];
  readonly onOpenDocument: (source: SelectionEntry) => void;
}

interface MessageItemProps extends MessageListProps {
  readonly index: number;
}

function MessageItem({ messages, index, onOpenDocument }: MessageItemProps) {
  const message = messages[index];
  if (!message) return null;
  const text = textOf(message);
  const sources = sourcesAt(messages, index);
  if (message.role === 'user') return <UserMessage text={text} sources={sources} />;
  return (
    <AssistantMessage
      text={text}
      sources={sources}
      isInterrupted={message.metadata?.isInterrupted ?? false}
      onOpenDocument={onOpenDocument}
    />
  );
}

/** Toute la conversation ; un séparateur marque chaque changement de sélection */
export default function MessageList({ messages, onOpenDocument }: MessageListProps) {
  return (
    <ol aria-label="Conversation" className="flex flex-col gap-4">
      {messages.map((message, index) => (
        <Fragment key={message.id}>
          {startsSegment(messages, index) && <SegmentSeparator />}
          <MessageItem messages={messages} index={index} onOpenDocument={onOpenDocument} />
        </Fragment>
      ))}
    </ol>
  );
}
