'use client';

import type { DocumentChunk } from '@murphy/contract/messages';
import { useTheme } from '@/components/providers/ThemeProvider';

interface SourceItemProps {
  chunk: DocumentChunk;
}

export default function SourceItem({ chunk }: SourceItemProps) {
  const theme = useTheme();

  return (
    <div className="source-item" style={{ borderColor: theme.colors.tertiary, opacity: 0.8 }}>
      <div className="flex justify-between gap-2">
        <div className="flex-1">
          <div className="font-semibold">{chunk.title ?? chunk.chunkId}</div>
          <div className="text-xs opacity-70">{chunk.chunkId}</div>
          {chunk.type && <div className="text-xs opacity-60">{chunk.type}</div>}
        </div>
        <div className="font-semibold whitespace-nowrap">
          {`${(chunk.score * 100).toFixed(0)}%`}
        </div>
      </div>
    </div>
  );
}
