import { describe, expect, it } from 'vitest';
import { canExplain, isOverBudget, sumContentLength } from '@/lib/selectionBudget';
import type { SelectionEntry } from '@/stores/selectionStore';

const entryOf = (contentLength: number): SelectionEntry => ({
  identifier: `doc-${contentLength}`,
  title: 'Titre',
  documentType: 'article',
  contentLength,
});

describe('selectionBudget', () => {
  it('sums the lengths of the texts', () => {
    expect(sumContentLength([entryOf(30), entryOf(70)])).toBe(100);
  });

  it('is over budget strictly above it', () => {
    expect(isOverBudget([entryOf(100)], 100)).toBe(false);
    expect(isOverBudget([entryOf(101)], 100)).toBe(true);
  });

  it.each([
    ['an empty selection', [], 100, false],
    ['no budget yet', [entryOf(10)], undefined, false],
    ['a selection over budget', [entryOf(101)], 100, false],
    ['a selection within budget', [entryOf(10)], 100, true],
  ])('explains %s: %s', (_case, entries, budget, expected) => {
    expect(canExplain(entries, budget)).toBe(expected);
  });
});
