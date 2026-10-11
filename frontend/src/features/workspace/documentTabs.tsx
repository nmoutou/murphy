import type { DockviewApi, IDockviewPanelProps } from 'dockview-react';
import type { DocumentType, Passage, SearchResult } from '@murphy/contract/search';
import type { DisplayedErrorCode } from '@/lib/api/apiError';
import DocumentPanel from '@/features/document/DocumentPanel';
import { useErrorStore } from '@/stores/errorStore';
import type { FixedPanelKind } from './panelRegistry';

export const DOCUMENT_COMPONENT = 'document';
const DOCUMENT_ID_PREFIX = `${DOCUMENT_COMPONENT}:`;
const RESULTS_PANEL: FixedPanelKind = 'results';

export interface DocumentPanelParams {
  readonly identifier: string;
  readonly documentType: DocumentType;
  readonly nature?: string;
  readonly passage?: Passage;
}

/** Un onglet par document : le rouvrir l'active. Il s'ouvre près des Résultats, s'ils sont ouverts */
export const openDocument = (api: DockviewApi, result: SearchResult): void => {
  const { identifier, title, documentType, nature, passages } = result;
  const id = `${DOCUMENT_ID_PREFIX}${identifier}`;
  const openedPanel = api.getPanel(id);
  if (openedPanel) {
    openedPanel.api.setActive();
    return;
  }
  const resultsGroup = api.getPanel(RESULTS_PANEL)?.group;
  const params: DocumentPanelParams = { identifier, documentType, nature, passage: passages[0] };
  api.addPanel({
    id,
    component: DOCUMENT_COMPONENT,
    title,
    params,
    position: resultsGroup ? { referenceGroup: resultsGroup } : undefined,
  });
};

/** Un document illisible ferme son onglet ; la modale dit pourquoi */
export const DocumentPanelAdapter = ({ api, params }: IDockviewPanelProps<DocumentPanelParams>) => {
  const handleError = (code: DisplayedErrorCode) => {
    useErrorStore.getState().showError(code);
    api.close();
  };
  return (
    <DocumentPanel identifier={params.identifier} passage={params.passage} onError={handleError} />
  );
};
