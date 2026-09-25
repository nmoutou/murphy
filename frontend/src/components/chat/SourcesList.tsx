'use client';

import type { DocumentChunk } from '@murphy/contract/messages';
import { useTheme } from '@/components/providers/ThemeProvider';
import SourceItem from './SourceItem';

interface SourcesListProps {
  chunks: DocumentChunk[];
  onChunkClick?: (chunk: DocumentChunk) => void;
}

export default function SourcesList({ chunks, onChunkClick }: SourcesListProps) {
  const theme = useTheme();

  if (!chunks || chunks.length === 0) {
    return null;
  }

  return (
    <div className="sources-list-header" style={{ borderColor: theme.colors.tertiary }}>
      <details className="cursor-pointer">
        <summary className="sources-list-summary">
          Sources ({chunks.length})
        </summary>
        <div className="sources-list-content">
          {chunks.map((chunk, idx) => (
            <SourceItem
              key={idx}
              chunk={chunk}
              onChunkClick={onChunkClick}
            />
          ))}
        </div>
      </details>
    </div>
  );
}
