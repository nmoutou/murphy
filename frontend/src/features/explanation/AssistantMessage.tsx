import { useMemo } from 'react';
import type { ComponentProps } from 'react';
import Markdown from 'react-markdown';
import type { Components } from 'react-markdown';
import type { SelectionEntry } from '@/stores/selectionStore';
import { linkCitations, readCitation } from './citations';

interface AssistantMessageProps {
  readonly text: string;
  readonly sources: readonly SelectionEntry[];
  readonly isInterrupted: boolean;
  readonly onOpenDocument: (source: SelectionEntry) => void;
}

const buildComponents = (
  sources: readonly SelectionEntry[],
  onOpenDocument: (source: SelectionEntry) => void,
): Components => ({
  // Un autre lien que le LLM aurait écrit reste du texte : la réponse ne mène qu'aux sources
  a: ({ href, children }: ComponentProps<'a'>) => {
    const position = readCitation(href);
    const source = position === undefined ? undefined : sources[position - 1];
    if (!source) return <>{position === undefined ? children : `[${position}]`}</>;
    return (
      <button
        type="button"
        title={source.title}
        onClick={() => onOpenDocument(source)}
        className="font-mono text-quaternary underline"
      >
        [{position}]
      </button>
    );
  },
});

export default function AssistantMessage({
  text,
  sources,
  isInterrupted,
  onOpenDocument,
}: AssistantMessageProps) {
  const components = useMemo(
    () => buildComponents(sources, onOpenDocument),
    [sources, onOpenDocument],
  );

  return (
    <li className="explanation-markdown flex flex-col gap-2">
      <Markdown components={components}>{linkCitations(text)}</Markdown>
      {isInterrupted && <p className="text-sm italic opacity-70">Réponse interrompue.</p>}
    </li>
  );
}
