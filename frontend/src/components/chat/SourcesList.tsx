'use client';

import type { DocumentChunk } from '@murphy/contract/messages';
import SourceItem from './SourceItem';

interface SourcesListProps {
  chunks: DocumentChunk[];
}

export default function SourcesList({ chunks }: SourcesListProps) {
  return (
    <div className="sources-list-header">
      <details className="cursor-pointer">
        <summary className="sources-list-summary">Sources ({chunks.length})</summary>
        <div className="sources-list-content">
          {chunks.map((chunk) => (
            <SourceItem key={chunk.chunkId} chunk={chunk} />
          ))}
        </div>
      </details>
    </div>
  );
}
