'use client';

import type { DocumentChunk } from '@murphy/contract/messages';
import { describeDocumentType } from '@/lib/documentTypeLabels';

interface SourceItemProps {
  chunk: DocumentChunk;
}

export default function SourceItem({ chunk }: SourceItemProps) {
  return (
    <div className="source-item">
      <div className="font-semibold">{chunk.title ?? chunk.chunkId}</div>
      <div className="text-xs opacity-70">{chunk.chunkId}</div>
      <div className="text-xs opacity-60">
        {describeDocumentType(chunk.documentType, chunk.nature)}
      </div>
    </div>
  );
}
