import InForceDot from '@/components/ui/InForceDot';
import type { SelectionEntry } from '@/stores/selectionStore';

interface SelectionListProps {
  readonly entries: readonly SelectionEntry[];
  readonly onOpenDocument: (entry: SelectionEntry) => void;
  readonly onRemove: (identifier: string) => void;
}

interface SelectionItemProps {
  readonly entry: SelectionEntry;
  readonly position: number;
  readonly onOpen: () => void;
  readonly onRemove: () => void;
}

function SelectionItem({ entry, position, onOpen, onRemove }: SelectionItemProps) {
  return (
    <li className="flex items-center gap-2 border-b border-secondary py-2">
      <span className="w-6 shrink-0 text-right font-mono text-xs">{position}</span>
      <InForceDot isInForce={entry.isInForce} />
      <button
        type="button"
        title={entry.title}
        onClick={onOpen}
        className="min-w-0 flex-1 truncate text-left font-mono text-sm text-quaternary hover:underline"
      >
        {entry.title}
      </button>
      <button
        type="button"
        aria-label={`Retirer ${entry.title} de la sélection`}
        onClick={onRemove}
        className="shrink-0 rounded px-1 opacity-60 hover:opacity-100"
      >
        ×
      </button>
    </li>
  );
}

/** Numérotée dans l'ordre des ajouts : `[n]` dans une réponse désigne le n-ième */
export default function SelectionList({ entries, onOpenDocument, onRemove }: SelectionListProps) {
  return (
    <ol aria-label="Documents sélectionnés" className="flex flex-col">
      {entries.map((entry, index) => (
        <SelectionItem
          key={entry.identifier}
          entry={entry}
          position={index + 1}
          onOpen={() => onOpenDocument(entry)}
          onRemove={() => onRemove(entry.identifier)}
        />
      ))}
    </ol>
  );
}
