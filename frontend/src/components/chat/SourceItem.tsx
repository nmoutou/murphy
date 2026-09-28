'use client';

import type { DocumentChunk } from '@murphy/contract/messages';

const PERCENT = 100;

interface SourceItemProps {
  chunk: DocumentChunk;
}

export default function SourceItem({ chunk }: SourceItemProps) {
  const scorePercent = `${(chunk.score * PERCENT).toFixed(0)}%`;

  return (
    <div className="source-item">
      <div className="flex justify-between gap-2">
        <div className="flex-1">
          <div className="font-semibold">{chunk.title ?? chunk.chunkId}</div>
          <div className="text-xs opacity-70">{chunk.chunkId}</div>
          {chunk.type && <div className="text-xs opacity-60">{chunk.type}</div>}
        </div>
        <div className="font-semibold whitespace-nowrap">{scorePercent}</div>
      </div>
    </div>
  );
}
