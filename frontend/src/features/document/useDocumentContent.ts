import { useEffect, useEffectEvent, useState } from 'react';
import type { DocumentContent } from '@murphy/contract/search';
import type { DisplayedErrorCode } from '@/lib/api/apiError';
import { reportApiError } from '@/lib/api/apiError';
import { fetchDocument } from '@/lib/api/documents';

/** Absent tant que le document charge ; la requête est annulée au démontage */
export const useDocumentContent = (
  identifier: string,
  onError: (code: DisplayedErrorCode) => void,
): DocumentContent | undefined => {
  const [loadedDocument, setLoadedDocument] = useState<DocumentContent>();
  // Un nouveau rappel à chaque rendu du parent ne doit pas relancer la requête
  const handleError = useEffectEvent(onError);

  useEffect(() => {
    const controller = new AbortController();
    const load = async () => {
      try {
        setLoadedDocument(await fetchDocument(identifier, controller.signal));
      } catch (error) {
        if (!controller.signal.aborted) handleError(reportApiError(error));
      }
    };
    void load();
    return () => controller.abort();
  }, [identifier]);

  return loadedDocument;
};
