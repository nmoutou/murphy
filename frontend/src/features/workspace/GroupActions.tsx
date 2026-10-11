'use client';

import { useState } from 'react';
import type { FocusEvent } from 'react';
import type { IDockviewHeaderActionsProps } from 'dockview-react';
import FixedPanelList from './FixedPanelList';
import type { FixedPanelKind } from './panelRegistry';
import { openFixedPanel } from './panelRegistry';
import { useClosedFixedPanels } from './useClosedFixedPanels';

interface ReopenMenuProps {
  readonly kinds: readonly FixedPanelKind[];
  readonly onReopen: (kind: FixedPanelKind) => void;
}

function ReopenMenu({ kinds, onReopen }: ReopenMenuProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleBlur = (event: FocusEvent<HTMLDivElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget)) setIsOpen(false);
  };
  const handleSelect = (kind: FixedPanelKind) => {
    setIsOpen(false);
    onReopen(kind);
  };

  return (
    <div className="relative" onBlur={handleBlur}>
      <button
        type="button"
        aria-label="Rouvrir un onglet"
        aria-expanded={isOpen}
        onClick={() => setIsOpen(!isOpen)}
        className="rounded-full px-2 text-tertiary hover:bg-secondary"
      >
        …
      </button>
      {isOpen && (
        <div className="absolute top-full right-0 z-10 rounded-lg bg-primary text-tertiary shadow-lg ring-1 ring-secondary">
          <FixedPanelList kinds={kinds} onSelect={handleSelect} />
        </div>
      )}
    </div>
  );
}

export default function GroupActions({ containerApi, group }: IDockviewHeaderActionsProps) {
  const closedKinds = useClosedFixedPanels(containerApi);

  const handleReopen = (kind: FixedPanelKind) => openFixedPanel(containerApi, kind, { group });

  return (
    <div className="flex h-full items-center px-2">
      <ReopenMenu kinds={closedKinds} onReopen={handleReopen} />
    </div>
  );
}
