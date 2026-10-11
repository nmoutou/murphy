import type { FunctionComponent } from 'react';
import type { DockviewApi, DockviewGroupPanel, IDockviewPanelProps } from 'dockview-react';
import ResultsPanel from '@/features/results/ResultsPanel';
import GraphPanel from '@/features/graph/GraphPanel';
import ExplanationPanel from '@/features/explanation/ExplanationPanel';
import { DOCUMENT_COMPONENT, DocumentPanelAdapter, openDocument } from './documentTabs';

const ResultsPanelAdapter = ({ containerApi }: IDockviewPanelProps) => (
  <ResultsPanel onOpenDocument={(result) => openDocument(containerApi, result)} />
);

/** Un panneau fixe a pour identifiant et pour composant Dockview son type : il est unique */
export const FIXED_PANELS = ['results', 'graph', 'explanation'] as const;

export type FixedPanelKind = (typeof FIXED_PANELS)[number];

interface PanelDefinition {
  readonly title: string;
  readonly icon: string;
  readonly component: FunctionComponent<IDockviewPanelProps>;
}

export const PANEL_DEFINITIONS: Record<FixedPanelKind, PanelDefinition> = {
  results: { title: 'Résultats', icon: 'search', component: ResultsPanelAdapter },
  graph: { title: 'Graphe', icon: 'graphe', component: GraphPanel },
  explanation: { title: 'Explication', icon: 'explaining', component: ExplanationPanel },
};

export const PANEL_COMPONENTS: Record<string, FunctionComponent<IDockviewPanelProps>> = {
  ...Object.fromEntries(FIXED_PANELS.map((kind) => [kind, PANEL_DEFINITIONS[kind].component])),
  [DOCUMENT_COMPONENT]: DocumentPanelAdapter,
};

export const isFixedPanelKind = (panelId: string): panelId is FixedPanelKind =>
  FIXED_PANELS.some((kind) => kind === panelId);

interface OpenFixedPanelOptions {
  readonly group?: DockviewGroupPanel;
  readonly isInactive?: boolean;
}

/** Sans groupe, Dockview prend le groupe actif, ou en crée un */
export const openFixedPanel = (
  api: DockviewApi,
  kind: FixedPanelKind,
  { group, isInactive = false }: OpenFixedPanelOptions = {},
): void => {
  api.addPanel({
    id: kind,
    component: kind,
    title: PANEL_DEFINITIONS[kind].title,
    position: group ? { referenceGroup: group } : undefined,
    inactive: isInactive,
  });
};
