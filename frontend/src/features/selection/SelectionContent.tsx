import type { SelectionEntry } from '@/stores/selectionStore';
import BudgetGauge from './BudgetGauge';
import SelectionList from './SelectionList';
import { canExplain, sumContentLength } from '@/lib/selectionBudget';

const EMPTY_INVITE = 'Ajoutez des documents depuis la recherche avec « + ».';

export interface SelectionContentProps {
  readonly entries: readonly SelectionEntry[];
  /** Absent avant qu'une recherche ait répondu */
  readonly budget?: number;
  /** Une réponse en cours bloque un nouveau résumé */
  readonly isAnswering: boolean;
  readonly onSummarize: () => void;
  readonly onOpenDocument: (entry: SelectionEntry) => void;
  readonly onRemove: (identifier: string) => void;
  readonly onClear: () => void;
}

type SelectedDocumentsProps = Pick<
  SelectionContentProps,
  'entries' | 'onOpenDocument' | 'onRemove'
>;

/** Sans document, une invite renvoie à la recherche : il n'y a rien à expliquer */
function SelectedDocuments({ entries, onOpenDocument, onRemove }: SelectedDocumentsProps) {
  return (
    <div className="min-h-0 flex-1 overflow-y-auto scrollbar">
      {entries.length === 0 ? (
        <p className="py-2 text-sm">{EMPTY_INVITE}</p>
      ) : (
        <SelectionList entries={entries} onOpenDocument={onOpenDocument} onRemove={onRemove} />
      )}
    </div>
  );
}

/** De haut en bas : « Résumer », la jauge, la liste, « Tout retirer » */
export default function SelectionContent({
  entries,
  budget,
  isAnswering,
  onSummarize,
  onOpenDocument,
  onRemove,
  onClear,
}: SelectionContentProps) {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 px-3 pb-3">
      <button
        type="button"
        disabled={isAnswering || !canExplain(entries, budget)}
        onClick={onSummarize}
        className="rounded-full bg-quaternary px-4 py-1 text-primary hover:opacity-80 disabled:opacity-40"
      >
        Résumer
      </button>
      {budget !== undefined && <BudgetGauge used={sumContentLength(entries)} budget={budget} />}
      <SelectedDocuments entries={entries} onOpenDocument={onOpenDocument} onRemove={onRemove} />
      {entries.length > 0 && (
        <button type="button" onClick={onClear} className="self-end text-sm hover:underline">
          Tout retirer
        </button>
      )}
    </div>
  );
}
