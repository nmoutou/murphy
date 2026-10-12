import { create } from 'zustand';
import type { SearchResult } from '@murphy/contract/search';

/** Ce que la sidebar et les sources d'un message affichent d'un document */
export type SelectionEntry = Pick<
  SearchResult,
  'identifier' | 'title' | 'documentType' | 'nature' | 'isInForce' | 'contentLength'
>;

interface SelectionState {
  /** Dans l'ordre des ajouts : `[n]` désigne le n-ième */
  readonly entries: readonly SelectionEntry[];
  /** Ajoute le document à la fin, ou le retire s'il y est déjà */
  readonly toggle: (document: SelectionEntry) => void;
  readonly remove: (identifier: string) => void;
  readonly clear: () => void;
}

/** Sans ses passages : une recherche ne change pas ce qu'on a choisi */
const toEntry = ({
  identifier,
  title,
  documentType,
  nature,
  isInForce,
  contentLength,
}: SelectionEntry): SelectionEntry => ({
  identifier,
  title,
  documentType,
  nature,
  isInForce,
  contentLength,
});

const without = (entries: readonly SelectionEntry[], identifier: string) =>
  entries.filter((entry) => entry.identifier !== identifier);

/** Survit à une nouvelle recherche, comme les onglets document ; pas à un rechargement */
export const useSelectionStore = create<SelectionState>()((set) => ({
  entries: [],
  toggle: (document) =>
    set(({ entries }) => ({
      entries: entries.some((entry) => entry.identifier === document.identifier)
        ? without(entries, document.identifier)
        : [...entries, toEntry(document)],
    })),
  remove: (identifier) => set(({ entries }) => ({ entries: without(entries, identifier) })),
  clear: () => set({ entries: [] }),
}));
