'use client';

import { useState } from 'react';
import type { FocusEvent } from 'react';
import type { IDockviewHeaderActionsProps } from 'dockview-react';
import ButtonIcon from '@/components/icons/ButtonIcon';
import FixedPanelList from './FixedPanelList';
import type { FixedPanelKind } from './panelRegistry';
import { openFixedPanel } from './panelRegistry';
import { useClosedFixedPanels } from './useClosedFixedPanels';

const ACTION_ICON_SIZE = 16;
const MIN_PANELS_TO_SPLIT = 2;
// Sur un écran étroit, deux groupes côte à côte seraient illisibles
const NARROW_SCREEN_QUERY = '(max-width: 640px)';

/** L'onglet actif part dans un nouveau groupe, à droite ou en dessous */
const splitActivePanel = ({ containerApi, group, activePanel }: IDockviewHeaderActionsProps) => {
  if (!activePanel) return;
  const isNarrow = window.matchMedia(NARROW_SCREEN_QUERY).matches;
  const newGroup = containerApi.addGroup({
    referenceGroup: group,
    direction: isNarrow ? 'below' : 'right',
  });
  activePanel.api.moveTo({ group: newGroup });
};

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

export default function GroupActions(props: IDockviewHeaderActionsProps) {
  const { containerApi, group, panels } = props;
  const closedKinds = useClosedFixedPanels(containerApi);

  const handleReopen = (kind: FixedPanelKind) => openFixedPanel(containerApi, kind, { group });

  return (
    <div className="flex h-full items-center gap-1 px-2">
      <ButtonIcon
        icon="sidebar"
        label="Scinder"
        size={ACTION_ICON_SIZE}
        onClick={() => splitActivePanel(props)}
        disabled={panels.length < MIN_PANELS_TO_SPLIT}
      />
      <ReopenMenu kinds={closedKinds} onReopen={handleReopen} />
    </div>
  );
}
