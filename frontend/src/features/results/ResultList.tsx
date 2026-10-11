import type { SearchResult } from '@murphy/contract/search';
import ResultItem from './ResultItem';

interface ResultListProps {
  readonly results: readonly SearchResult[];
  readonly onOpenDocument: (result: SearchResult) => void;
}

/** Dans l'ordre du classement */
export default function ResultList({ results, onOpenDocument }: ResultListProps) {
  return (
    <ol aria-label="Résultats">
      {results.map((result) => (
        <ResultItem key={result.identifier} result={result} onOpenDocument={onOpenDocument} />
      ))}
    </ol>
  );
}
