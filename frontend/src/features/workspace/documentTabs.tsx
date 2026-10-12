import type { DockviewApi, IDockviewPanelProps } from 'dockview-react';
import type { Passage } from '@murphy/contract/search';
import type { DisplayedErrorCode } from '@/lib/api/apiError';
import DocumentPanel from '@/features/document/DocumentPanel';
import { useErrorStore } from '@/stores/errorStore';
import type { FixedPanelKind } from './panelRegistry';

export const DOCUMENT_COMPONENT = 'document';
const DOCUMENT_ID_PREFIX = `${DOCUMENT_COMPONENT}:`;
const RESULTS_PANEL: FixedPanelKind = 'results';

export interface DocumentPanelParams {
  readonly identifier: string;
  /** Le passage à surligner ; absent quand on ouvre le document depuis la sélection */
  readonly passage?: Passage;
}

export interface DocumentTarget extends DocumentPanelParams {
  readonly title: string;
}

/** Un onglet par document : le rouvrir l'active. Il s'ouvre près de Recherche, si elle est ouverte */
export const openDocument = (
  api: DockviewApi,
  { identifier, title, passage }: DocumentTarget,
): void => {
  const id = `${DOCUMENT_ID_PREFIX}${identifier}`;
  const openedPanel = api.getPanel(id);
  if (openedPanel) {
    openedPanel.api.setActive();
    return;
  }
  const resultsGroup = api.getPanel(RESULTS_PANEL)?.group;
  const params: DocumentPanelParams = { identifier, passage };
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
