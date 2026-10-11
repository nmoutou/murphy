'use client';

import type { IWatermarkPanelProps } from 'dockview-react';
import FixedPanelList from './FixedPanelList';
import type { FixedPanelKind } from './panelRegistry';
import { openFixedPanel } from './panelRegistry';
import { useClosedFixedPanels } from './useClosedFixedPanels';

/** L'espace vide n'a plus de groupe, donc plus de menu : il propose lui-même les réouvertures */
export default function Watermark({ containerApi }: IWatermarkPanelProps) {
  const closedKinds = useClosedFixedPanels(containerApi);

  const handleReopen = (kind: FixedPanelKind) => openFixedPanel(containerApi, kind);

  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 text-tertiary">
      <p>Aucun onglet ouvert.</p>
      <FixedPanelList kinds={closedKinds} onSelect={handleReopen} />
    </div>
  );
}
