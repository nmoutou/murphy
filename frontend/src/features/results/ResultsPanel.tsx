'use client';

import type { SearchResult } from '@murphy/contract/search';
import { useSearchStore } from '@/stores/searchStore';
import Pagination from './Pagination';
import ResultList from './ResultList';

const LOADING_MESSAGE = 'Recherche…';
const EMPTY_MESSAGE = 'Aucun résultat.';

/** Une erreur ne laisse rien : la modale l'annonce */
function useStatusMessage(): string | undefined {
  const status = useSearchStore((state) => state.status);
  const resultCount = useSearchStore((state) => state.response?.results.length);
  if (status === 'loading') return LOADING_MESSAGE;
  if (status === 'success' && resultCount === 0) return EMPTY_MESSAGE;
  return undefined;
}

interface ResultsPanelProps {
  readonly onOpenDocument: (result: SearchResult) => void;
}

/** Pendant un changement de page, la pagination reste en place et montre déjà la page demandée */
export default function ResultsPanel({ onOpenDocument }: ResultsPanelProps) {
  const statusMessage = useStatusMessage();
  const isLoading = useSearchStore((state) => state.status === 'loading');
  const response = useSearchStore((state) => state.response);
  const page = useSearchStore((state) => state.page);
  const goToPage = useSearchStore((state) => state.goToPage);

  return (
    <section className="flex h-full flex-col text-tertiary">
      <div className="min-h-0 flex-1 overflow-y-auto px-4 scrollbar">
        {statusMessage && (
          <p role="status" className="py-4">
            {statusMessage}
          </p>
        )}
        {response && !isLoading && (
          <ResultList results={response.results} onOpenDocument={onOpenDocument} />
        )}
      </div>
      {response && <Pagination page={page} pageCount={response.pageCount} onGoToPage={goToPage} />}
    </section>
  );
}
