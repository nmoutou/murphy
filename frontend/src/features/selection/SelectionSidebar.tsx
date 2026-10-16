'use client';

import { useState } from 'react';
import { useSearchStore } from '@/stores/searchStore';
import type { SelectionEntry } from '@/stores/selectionStore';
import { useSelectionStore } from '@/stores/selectionStore';
import type { SelectionContentProps } from './SelectionContent';
import SelectionContent from './SelectionContent';

const SIDEBAR_LABEL = 'Sélection';

/** Repliée, la bande est trop étroite pour « « » et le badge côte à côte */
const COLLAPSIBLE_LAYOUT = {
  collapsed: { aside: 'w-14 items-center', header: 'flex-col px-0', toggle: 'flex-col' },
  expanded: { aside: 'w-80', header: 'px-3', toggle: '' },
} as const;

interface SelectionSidebarProps {
  readonly isAnswering: boolean;
  readonly onSummarize: () => void;
  readonly onOpenDocument: (entry: SelectionEntry) => void;
}

const useContentProps = (props: SelectionSidebarProps): SelectionContentProps => ({
  ...props,
  entries: useSelectionStore((state) => state.entries),
  budget: useSearchStore((state) => state.contextBudget),
  onRemove: useSelectionStore((state) => state.remove),
  onClear: useSelectionStore((state) => state.clear),
});

interface CountBadgeProps {
  readonly count: number;
}

function CountBadge({ count }: CountBadgeProps) {
  return (
    <span className="rounded-full bg-quaternary px-2 font-mono text-xs text-primary">{count}</span>
  );
}

interface CollapsibleSidebarProps {
  readonly content: SelectionContentProps;
}

/** À droite de l'espace de travail, hors de Dockview : visible depuis tous les onglets */
function CollapsibleSidebar({ content }: CollapsibleSidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(true);
  const count = content.entries.length;
  const layout = COLLAPSIBLE_LAYOUT[isCollapsed ? 'collapsed' : 'expanded'];

  return (
    <aside
      aria-label={SIDEBAR_LABEL}
      className={`hidden shrink-0 flex-col border-l border-secondary bg-primary text-tertiary md:flex ${layout.aside}`}
    >
      <header className={`flex items-center justify-between gap-2 py-3 ${layout.header}`}>
        {!isCollapsed && <h2 className="font-mono text-quaternary">{SIDEBAR_LABEL}</h2>}
        <button
          type="button"
          aria-label={isCollapsed ? `Déplier la sélection (${count})` : 'Replier la sélection'}
          aria-expanded={!isCollapsed}
          onClick={() => setIsCollapsed(!isCollapsed)}
          className={`flex items-center gap-2 rounded px-1 hover:opacity-80 ${layout.toggle}`}
        >
          {isCollapsed ? '«' : '»'}
          <CountBadge count={count} />
        </button>
      </header>
      {!isCollapsed && <SelectionContent {...content} />}
    </aside>
  );
}

interface DrawerButtonProps {
  readonly count: number;
  readonly onOpen: () => void;
}

function DrawerButton({ count, onOpen }: DrawerButtonProps) {
  return (
    <button
      type="button"
      aria-label={`Afficher la sélection (${count})`}
      onClick={onOpen}
      className="fixed right-4 bottom-4 z-20 flex items-center gap-2 rounded-full bg-secondary px-4 py-2 text-tertiary shadow-lg md:hidden"
    >
      {SIDEBAR_LABEL}
      <CountBadge count={count} />
    </button>
  );
}

/** Sous `md`, un bouton flottant ouvre la sélection en tiroir */
function SelectionDrawer({ content }: CollapsibleSidebarProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!isOpen)
    return <DrawerButton count={content.entries.length} onOpen={() => setIsOpen(true)} />;
  return (
    <div className="fixed inset-0 z-30 md:hidden">
      <div
        aria-hidden
        className="absolute inset-0 bg-primary/70"
        onClick={() => setIsOpen(false)}
      />
      <aside
        aria-label={SIDEBAR_LABEL}
        className="absolute inset-y-0 right-0 flex w-80 max-w-full flex-col bg-primary text-tertiary"
      >
        <header className="flex items-center justify-between px-3 py-3">
          <h2 className="font-mono text-quaternary">{SIDEBAR_LABEL}</h2>
          <button type="button" aria-label="Fermer la sélection" onClick={() => setIsOpen(false)}>
            ×
          </button>
        </header>
        <SelectionContent {...content} />
      </aside>
    </div>
  );
}

export default function SelectionSidebar(props: SelectionSidebarProps) {
  const content = useContentProps(props);

  return (
    <>
      <CollapsibleSidebar content={content} />
      <SelectionDrawer content={content} />
    </>
  );
}
