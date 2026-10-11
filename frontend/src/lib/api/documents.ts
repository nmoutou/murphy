import type { DocumentContent } from '@murphy/contract/search';
import { documentContentSchema } from '@murphy/contract/search';
import { requestApi } from './request';

const DOCUMENTS_PATH = '/documents';

/** Un identifiant n'est pas garanti sûr dans un chemin d'URL */
export const fetchDocument = (identifier: string, signal: AbortSignal): Promise<DocumentContent> =>
  requestApi(
    `${DOCUMENTS_PATH}/${encodeURIComponent(identifier)}`,
    { signal },
    documentContentSchema,
  );
