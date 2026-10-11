'use client';

import type { MouseEvent, PointerEvent } from 'react';
import type { IDockviewPanelHeaderProps } from 'dockview-react';
import Icon from '@/components/icons/Icon';
import { isFixedPanelKind, PANEL_DEFINITIONS } from './panelRegistry';

const TAB_ICON_SIZE = 14;

// Sans cela, presser le bouton activerait ou glisserait l'onglet avant de le fermer
const handleClosePointerDown = (event: PointerEvent<HTMLButtonElement>) => event.preventDefault();

/** Seul un panneau fixe a une icône */
const selectTabIcon = (panelId: string): string | undefined =>
  isFixedPanelKind(panelId) ? PANEL_DEFINITIONS[panelId].icon : undefined;

/** Le titre est tronqué ; l'infobulle le donne en entier */
export default function PanelTab({ api }: IDockviewPanelHeaderProps) {
  const title = api.title ?? '';
  const icon = selectTabIcon(api.id);

  const handleClose = (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    api.close();
  };

  return (
    <div title={title} className="flex h-full max-w-64 items-center gap-2 px-3">
      {icon && <Icon icon={icon} size={TAB_ICON_SIZE} />}
      <span className="truncate">{title}</span>
      <button
        type="button"
        aria-label={`Fermer l'onglet ${title}`}
        onPointerDown={handleClosePointerDown}
        onClick={handleClose}
        className="rounded px-1 opacity-60 hover:opacity-100"
      >
        ×
      </button>
    </div>
  );
}
