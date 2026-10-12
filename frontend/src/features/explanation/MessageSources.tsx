import InForceDot from '@/components/ui/InForceDot';
import type { SelectionEntry } from '@/stores/selectionStore';

interface MessageSourcesProps {
  readonly sources: readonly SelectionEntry[];
}

/** La sélection au moment de la question, dans son ordre : `[n]` désigne la n-ième */
export default function MessageSources({ sources }: MessageSourcesProps) {
  return (
    <details className="mt-1 text-sm">
      <summary className="cursor-pointer select-none opacity-80">
        Sources ({sources.length})
      </summary>
      <ol className="mt-1 flex flex-col gap-1">
        {sources.map((source, index) => (
          <li key={source.identifier} className="flex items-center gap-2">
            <span className="w-6 shrink-0 text-right font-mono text-xs">{index + 1}</span>
            <InForceDot isInForce={source.isInForce} />
            <span className="truncate font-mono" title={source.title}>
              {source.title}
            </span>
          </li>
        ))}
      </ol>
    </details>
  );
}
