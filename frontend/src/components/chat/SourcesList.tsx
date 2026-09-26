'use client';

import type { DocumentChunk } from '@murphy/contract/messages';
import { useTheme } from '@/components/providers/ThemeProvider';
import SourceItem from './SourceItem';

interface SourcesListProps {
  chunks: DocumentChunk[];
}

export default function SourcesList({ chunks }: SourcesListProps) {
  const theme = useTheme();

  return (
    <div className="sources-list-header" style={{ borderColor: theme.colors.tertiary }}>
      <details className="cursor-pointer">
        <summary className="sources-list-summary">
          Sources ({chunks.length})
        </summary>
        <div className="sources-list-content">
          {chunks.map((chunk) => (
            <SourceItem key={chunk.chunkId} chunk={chunk} />
          ))}
        </div>
      </details>
    </div>
  );
}
