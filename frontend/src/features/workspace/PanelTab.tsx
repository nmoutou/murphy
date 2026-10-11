'use client';

import type { MouseEvent, PointerEvent } from 'react';
import type { IDockviewPanelHeaderProps } from 'dockview-react';
import Icon from '@/components/icons/Icon';
import { selectDocumentIcon } from '@/features/results/documentIcons';
import type { DocumentPanelParams } from './documentTabs';
import { isFixedPanelKind, PANEL_DEFINITIONS } from './panelRegistry';

const TAB_ICON_SIZE = 14;

// Sans cela, presser le bouton activerait ou glisserait l'onglet avant de le fermer
const handleClosePointerDown = (event: PointerEvent<HTMLButtonElement>) => event.preventDefault();

/** Un panneau fixe n'a pas de paramètres : seul un document en porte */
type PanelTabProps = IDockviewPanelHeaderProps<Partial<DocumentPanelParams>>;

const selectTabIcon = ({ api, params }: PanelTabProps): string | undefined => {
  if (isFixedPanelKind(api.id)) return PANEL_DEFINITIONS[api.id].icon;
  return params.documentType && selectDocumentIcon(params.documentType, params.nature);
};

/** Le titre est tronqué ; l'infobulle le donne en entier */
export default function PanelTab(props: PanelTabProps) {
  const { api } = props;
  const title = api.title ?? '';
  const icon = selectTabIcon(props);

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
