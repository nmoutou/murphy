import type { SelectionEntry } from '@/stores/selectionStore';
import MessageSources from './MessageSources';

interface UserMessageProps {
  readonly text: string;
  readonly sources: readonly SelectionEntry[];
}

export default function UserMessage({ text, sources }: UserMessageProps) {
  return (
    <li className="flex flex-col items-end">
      <p className="max-w-[80%] rounded-2xl bg-secondary px-4 py-2 whitespace-pre-wrap text-quaternary">
        {text}
      </p>
      <MessageSources sources={sources} />
    </li>
  );
}
