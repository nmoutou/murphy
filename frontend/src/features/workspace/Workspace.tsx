'use client';

import { useState } from 'react';
import { DockviewReact, themeDark } from 'dockview-react';
import type { DockviewApi, DockviewReadyEvent, DockviewTheme } from 'dockview-react';
import { applyDefaultLayout } from './defaultLayout';
import GroupActions from './GroupActions';
import PanelTab from './PanelTab';
import { PANEL_COMPONENTS } from './panelRegistry';
import SelectionSidebarAdapter from './SelectionSidebarAdapter';
import Watermark from './Watermark';

/** Le thème sombre de Dockview, recoloré par `.dockview-theme-murphy` dans globals.css */
const MURPHY_THEME: DockviewTheme = {
  ...themeDark,
  name: 'murphy',
  className: `${themeDark.className} dockview-theme-murphy`,
};

/** Le seul composant, avec ceux qu'il déclare, à connaître Dockview */
export default function Workspace() {
  // La sidebar, hors de Dockview, agit sur ses onglets
  const [api, setApi] = useState<DockviewApi>();

  const handleReady = ({ api: readyApi }: DockviewReadyEvent) => {
    applyDefaultLayout(readyApi);
    setApi(readyApi);
  };

  return (
    // min-w-0 : Dockview fixe ses largeurs en px, qui sinon imposeraient sa largeur passée au body
    <div className="flex min-h-0 min-w-0 flex-1 bg-primary">
      {/* overflow-hidden : un panneau jamais affiché reste posé sous la grille et ferait défiler la page */}
      <div className="min-w-0 flex-1 overflow-hidden">
        <DockviewReact
          theme={MURPHY_THEME}
          components={PANEL_COMPONENTS}
          // Par défaut, un onglet masqué est retiré du DOM et perd sa position de défilement
          defaultRenderer="always"
          onReady={handleReady}
          defaultTabComponent={PanelTab}
          rightHeaderActionsComponent={GroupActions}
          watermarkComponent={Watermark}
        />
      </div>
      {api && <SelectionSidebarAdapter api={api} />}
    </div>
  );
}
