import type { DockviewApi } from 'dockview-react';
import SelectionSidebar from '@/features/selection/SelectionSidebar';
import { summarize, useIsAnswering } from '@/stores/explanationStore';
import { openDocument } from './documentTabs';
import { showFixedPanel } from './panelRegistry';

interface SelectionSidebarAdapterProps {
  readonly api: DockviewApi;
}

/** Ouvre un document sans passage à surligner ; « Résumer » écrit dans l'onglet Explications */
export default function SelectionSidebarAdapter({ api }: SelectionSidebarAdapterProps) {
  const isAnswering = useIsAnswering();

  const handleSummarize = () => {
    void summarize();
    showFixedPanel(api, 'explanation');
  };

  return (
    <SelectionSidebar
      isAnswering={isAnswering}
      onOpenDocument={(entry) => openDocument(api, entry)}
      onSummarize={handleSummarize}
    />
  );
}
