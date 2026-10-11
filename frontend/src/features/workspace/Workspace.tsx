'use client';

import { DockviewReact, themeDark } from 'dockview-react';
import type { DockviewReadyEvent, DockviewTheme } from 'dockview-react';
import { applyDefaultLayout } from './defaultLayout';
import GroupActions from './GroupActions';
import PanelTab from './PanelTab';
import { PANEL_COMPONENTS } from './panelRegistry';
import Watermark from './Watermark';

/** Le thème sombre de Dockview, recoloré par `.dockview-theme-murphy` dans globals.css */
const MURPHY_THEME: DockviewTheme = {
  ...themeDark,
  name: 'murphy',
  className: `${themeDark.className} dockview-theme-murphy`,
};

const handleReady = ({ api }: DockviewReadyEvent) => applyDefaultLayout(api);

/** Le seul composant, avec ceux qu'il déclare, à connaître Dockview */
export default function Workspace() {
  return (
    <div className="min-h-0 flex-1 bg-primary">
      <DockviewReact
        theme={MURPHY_THEME}
        components={PANEL_COMPONENTS}
        onReady={handleReady}
        defaultTabComponent={PanelTab}
        rightHeaderActionsComponent={GroupActions}
        watermarkComponent={Watermark}
      />
    </div>
  );
}
