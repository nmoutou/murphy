import type { SearchResult } from '@murphy/contract/search';
import ResultItem from './ResultItem';

interface ResultListProps {
  readonly results: readonly SearchResult[];
  readonly selectedIdentifiers: ReadonlySet<string>;
  readonly onOpenDocument: (result: SearchResult) => void;
  readonly onToggleSelection: (result: SearchResult) => void;
}

/** Dans l'ordre du classement */
export default function ResultList({
  results,
  selectedIdentifiers,
  onOpenDocument,
  onToggleSelection,
}: ResultListProps) {
  return (
    <ol aria-label="Résultats">
      {results.map((result) => (
        <ResultItem
          key={result.identifier}
          result={result}
          isSelected={selectedIdentifiers.has(result.identifier)}
          onOpenDocument={onOpenDocument}
          onToggleSelection={onToggleSelection}
        />
      ))}
    </ol>
  );
}
