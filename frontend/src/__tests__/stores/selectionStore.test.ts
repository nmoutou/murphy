import { beforeEach, describe, expect, it } from 'vitest';
import type { SearchResult } from '@murphy/contract/search';
import { useSelectionStore } from '@/stores/selectionStore';

const resultOf = (identifier: string): SearchResult => ({
  identifier,
  title: `Titre ${identifier}`,
  documentType: 'article',
  isInForce: true,
  contentLength: 100,
  passages: [{ chunkId: `${identifier}-1`, text: 'extrait', start: 0, end: 7 }],
});

const identifiers = () => useSelectionStore.getState().entries.map((entry) => entry.identifier);

beforeEach(() => {
  useSelectionStore.setState(useSelectionStore.getInitialState(), true);
});

describe('selectionStore', () => {
  it('adds the documents in order, without their passages', () => {
    const { toggle } = useSelectionStore.getState();

    toggle(resultOf('B'));
    toggle(resultOf('A'));

    expect(identifiers()).toEqual(['B', 'A']);
    expect(useSelectionStore.getState().entries[0]).not.toHaveProperty('passages');
  });

  it('removes a selected document when toggled again, the others keeping their order', () => {
    const { toggle } = useSelectionStore.getState();
    ['A', 'B', 'C'].forEach((identifier) => toggle(resultOf(identifier)));

    toggle(resultOf('B'));

    expect(identifiers()).toEqual(['A', 'C']);
  });

  it('removes one document, or all of them', () => {
    const { toggle, remove, clear } = useSelectionStore.getState();
    ['A', 'B'].forEach((identifier) => toggle(resultOf(identifier)));

    remove('A');
    expect(identifiers()).toEqual(['B']);

    clear();
    expect(identifiers()).toEqual([]);
  });
});
