import type { FixedPanelKind } from './panelRegistry';
import { PANEL_DEFINITIONS } from './panelRegistry';

const ALL_OPEN_MESSAGE = 'Tous les onglets sont ouverts.';
const OPEN_ACTION = 'Ouvrir';

interface FixedPanelListProps {
  readonly kinds: readonly FixedPanelKind[];
  readonly onSelect: (kind: FixedPanelKind) => void;
}

/** Les panneaux fixes à rouvrir, communs au menu d'un groupe et à l'espace vide */
export default function FixedPanelList({ kinds, onSelect }: FixedPanelListProps) {
  if (kinds.length === 0) {
    return <p className="px-3 py-2 text-sm whitespace-nowrap">{ALL_OPEN_MESSAGE}</p>;
  }
  return (
    <ul className="flex flex-col py-1">
      {kinds.map((kind) => (
        <li key={kind}>
          <button
            type="button"
            onClick={() => onSelect(kind)}
            className="w-full px-3 py-1 text-left text-sm whitespace-nowrap hover:bg-secondary"
          >
            {OPEN_ACTION} {PANEL_DEFINITIONS[kind].title}
          </button>
        </li>
      ))}
    </ul>
  );
}
