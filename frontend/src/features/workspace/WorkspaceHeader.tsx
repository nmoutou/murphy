'use client';

import Logo from '@/components/icons/Logo';
import SearchBar from '@/components/ui/SearchBar';
import PageSizeSelect from '@/features/results/PageSizeSelect';
import { useSearchStore } from '@/stores/searchStore';

const HEADER_LOGO_WIDTH = 120;

/**
 * Une nouvelle question remplace la précédente, sans quitter l'espace de travail ; le choix de
 * la taille attend une première réponse, qui donne les tailles permises
 */
export default function WorkspaceHeader() {
  const question = useSearchStore((state) => state.question);
  const submit = useSearchStore((state) => state.submit);
  const pageSize = useSearchStore((state) => state.pageSize);
  const pageSizes = useSearchStore((state) => state.response?.pageSizes);
  const setPageSize = useSearchStore((state) => state.setPageSize);

  return (
    <header className="flex items-center gap-4 px-4 py-3">
      <Logo width={HEADER_LOGO_WIDTH} />
      <SearchBar variant="header" initialQuestion={question} onSubmit={submit} />
      {pageSize !== undefined && pageSizes && (
        <PageSizeSelect pageSize={pageSize} pageSizes={pageSizes} onChange={setPageSize} />
      )}
    </header>
  );
}
