'use client';

import SearchBar from '@/components/ui/SearchBar';
import { useSearchStore } from '@/stores/searchStore';
import PageSizeSelect from './PageSizeSelect';

/**
 * Une nouvelle question remplace la précédente ; le choix de la taille attend une première
 * réponse, qui donne les tailles permises
 */
export default function ResultsHeader() {
  const question = useSearchStore((state) => state.question);
  const submit = useSearchStore((state) => state.submit);
  const pageSize = useSearchStore((state) => state.pageSize);
  const pageSizes = useSearchStore((state) => state.response?.pageSizes);
  const setPageSize = useSearchStore((state) => state.setPageSize);

  return (
    <header className="flex items-center gap-4 px-4 py-3">
      <SearchBar variant="header" initialQuestion={question} onSubmit={submit} />
      {pageSize !== undefined && pageSizes && (
        <PageSizeSelect pageSize={pageSize} pageSizes={pageSizes} onChange={setPageSize} />
      )}
    </header>
  );
}
