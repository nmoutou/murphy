'use client';

import Logo from '@/components/icons/Logo';
import SearchBar from '@/components/ui/SearchBar';
import { useSearchStore } from '@/stores/searchStore';

const HEADER_LOGO_WIDTH = 120;

/** Une nouvelle question remplace la précédente, sans quitter l'espace de travail */
export default function WorkspaceHeader() {
  const question = useSearchStore((state) => state.question);
  const submit = useSearchStore((state) => state.submit);

  return (
    <header className="flex items-center gap-4 px-4 py-3">
      <Logo width={HEADER_LOGO_WIDTH} />
      <SearchBar variant="header" initialQuestion={question} onSubmit={submit} />
    </header>
  );
}
