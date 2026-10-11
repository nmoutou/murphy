import type { FunctionComponent } from 'react';
import type { DockviewApi, DockviewGroupPanel, IDockviewPanelProps } from 'dockview-react';
import ResultsPanel from '@/features/results/ResultsPanel';
import GraphPanel from '@/features/graph/GraphPanel';
import ExplanationPanel from '@/features/explanation/ExplanationPanel';

/** Un panneau fixe a pour identifiant et pour composant Dockview son type : il est unique */
export const FIXED_PANELS = ['results', 'graph', 'explanation'] as const;

export type FixedPanelKind = (typeof FIXED_PANELS)[number];

interface PanelDefinition {
  readonly title: string;
  readonly icon: string;
  readonly component: FunctionComponent<IDockviewPanelProps>;
}

export const PANEL_DEFINITIONS: Record<FixedPanelKind, PanelDefinition> = {
  results: { title: 'Résultats', icon: 'folder', component: ResultsPanel },
  graph: { title: 'Graphe', icon: 'window', component: GraphPanel },
  explanation: { title: 'Explication', icon: 'edit', component: ExplanationPanel },
};

export const PANEL_COMPONENTS: Record<
  string,
  FunctionComponent<IDockviewPanelProps>
> = Object.fromEntries(FIXED_PANELS.map((kind) => [kind, PANEL_DEFINITIONS[kind].component]));

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
