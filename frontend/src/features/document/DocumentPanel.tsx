'use client';

import type { Passage } from '@murphy/contract/search';
import type { DisplayedErrorCode } from '@/lib/api/apiError';
import { splitAroundPassage } from './splitAroundPassage';
import { useDocumentContent } from './useDocumentContent';

const LOADING_MESSAGE = 'Chargement du document…';

// Stable : un ref recréé à chaque rendu ramènerait le passage sous les yeux à chaque rendu
const scrollToPassage = (mark: HTMLElement | null) => mark?.scrollIntoView({ block: 'center' });

interface DocumentPanelProps {
  readonly identifier: string;
  /** Le passage le mieux classé de la recherche, surligné */
  readonly passage?: Passage;
  readonly onError: (code: DisplayedErrorCode) => void;
}

export default function DocumentPanel({ identifier, passage, onError }: DocumentPanelProps) {
  const loadedDocument = useDocumentContent(identifier, onError);

  if (!loadedDocument) {
    return (
      <p role="status" className="px-4 py-4 text-tertiary">
        {LOADING_MESSAGE}
      </p>
    );
  }
  const parts = splitAroundPassage(loadedDocument.content, passage);

  return (
    <article className="h-full overflow-y-auto px-4 py-4 text-tertiary scrollbar">
      <h2 className="mb-4 font-mono text-quaternary">{loadedDocument.title}</h2>
      <p className="whitespace-pre-wrap">
        {parts.before}
        {parts.passage && (
          <mark ref={scrollToPassage} className="rounded bg-highlight text-primary">
            {parts.passage}
          </mark>
        )}
        {parts.after}
      </p>
    </article>
  );
}
