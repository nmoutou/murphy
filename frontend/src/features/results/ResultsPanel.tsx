'use client';

import { useSearchStore } from '@/stores/searchStore';

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

export default function ResultsPanel() {
  const statusMessage = useStatusMessage();

  return (
    <section className="h-full overflow-y-auto p-4 text-tertiary scrollbar">
      {statusMessage && <p role="status">{statusMessage}</p>}
    </section>
  );
}
