import { useCallback, useMemo, useSyncExternalStore } from 'react';
import type { DockviewApi } from 'dockview-react';
import type { FixedPanelKind } from './panelRegistry';
import { FIXED_PANELS } from './panelRegistry';

const KIND_SEPARATOR = ' ';
const NO_CLOSED_PANEL = '';

// Une chaîne plutôt qu'un tableau : useSyncExternalStore compare les instantanés par identité
const readClosedKinds = (api: DockviewApi): string =>
  FIXED_PANELS.filter((kind) => api.getPanel(kind) === undefined).join(KIND_SEPARATOR);

/** Les panneaux fixes ouverts nulle part, tenus à jour à chaque ajout ou fermeture */
export const useClosedFixedPanels = (api: DockviewApi): readonly FixedPanelKind[] => {
  const subscribe = useCallback(
    (onChange: () => void) => {
      const added = api.onDidAddPanel(onChange);
      const removed = api.onDidRemovePanel(onChange);
      return () => {
        added.dispose();
        removed.dispose();
      };
    },
    [api],
  );
  const closedKinds = useSyncExternalStore(
    subscribe,
    () => readClosedKinds(api),
    () => NO_CLOSED_PANEL,
  );
  return useMemo(
    () => FIXED_PANELS.filter((kind) => closedKinds.split(KIND_SEPARATOR).includes(kind)),
    [closedKinds],
  );
};
