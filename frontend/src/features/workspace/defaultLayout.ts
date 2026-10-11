import type { DockviewApi } from 'dockview-react';
import { FIXED_PANELS, openFixedPanel } from './panelRegistry';

/** Un groupe, les trois panneaux fixes, Résultats actif */
export const applyDefaultLayout = (api: DockviewApi): void => {
  FIXED_PANELS.forEach((kind, index) => openFixedPanel(api, kind, { isInactive: index > 0 }));
};
