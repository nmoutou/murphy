import type { SearchResult } from '@murphy/contract/search';
import InForceDot from '@/components/ui/InForceDot';

interface ResultItemProps {
  readonly result: SearchResult;
  readonly isSelected: boolean;
  readonly onOpenDocument: (result: SearchResult) => void;
  readonly onToggleSelection: (result: SearchResult) => void;
}

interface SelectionToggleProps {
  readonly title: string;
  readonly isSelected: boolean;
  readonly onToggle: () => void;
}

function SelectionToggle({ title, isSelected, onToggle }: SelectionToggleProps) {
  const label = isSelected ? `Retirer ${title} de la sélection` : `Ajouter ${title} à la sélection`;
  const style = isSelected ? 'bg-tertiary text-primary' : 'text-tertiary ring-1 ring-tertiary';

  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onToggle}
      className={`flex size-6 shrink-0 items-center justify-center rounded-full hover:opacity-80 ${style}`}
    >
      {isSelected ? '−' : '+'}
    </button>
  );
}

interface ResultSummaryProps {
  readonly result: SearchResult;
  readonly onOpenDocument: (result: SearchResult) => void;
}

function ResultSummary({ result, onOpenDocument }: ResultSummaryProps) {
  const { title, isInForce, passages } = result;
  // Le mieux classé
  const passage = passages[0];

  return (
    <article className="min-w-0 flex-1">
      <div className="flex items-center gap-2">
        <InForceDot isInForce={isInForce} />
        <button
          type="button"
          onClick={() => onOpenDocument(result)}
          className="text-left font-mono text-quaternary hover:underline"
        >
          {title}
        </button>
      </div>
      {passage && <p className="mt-1 line-clamp-3 text-sm">{passage.text}</p>}
    </article>
  );
}

export default function ResultItem({
  result,
  isSelected,
  onOpenDocument,
  onToggleSelection,
}: ResultItemProps) {
  return (
    <li className="flex items-center gap-3 border-b border-secondary py-3">
      <SelectionToggle
        title={result.title}
        isSelected={isSelected}
        onToggle={() => onToggleSelection(result)}
      />
      <ResultSummary result={result} onOpenDocument={onOpenDocument} />
    </li>
  );
}
