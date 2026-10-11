import { describe, expect, it } from 'vitest';
import { buildPageItems } from '@/features/results/pageItems';

describe('buildPageItems', () => {
  it.each([
    [1, 1, [1]],
    [1, 3, [1, 2, 3]],
    [1, 10, [1, 2, 'ellipsis-after', 10]],
    [5, 10, [1, 'ellipsis-before', 4, 5, 6, 'ellipsis-after', 10]],
    [10, 10, [1, 'ellipsis-before', 9, 10]],
    [4, 4, [1, 2, 3, 4]],
  ])('page %i of %i gives %j', (page, pageCount, expected) => {
    expect(buildPageItems(page, pageCount)).toEqual(expected);
  });

  it('shows a single hidden page instead of an ellipsis', () => {
    expect(buildPageItems(4, 10)).toEqual([1, 2, 3, 4, 5, 'ellipsis-after', 10]);
  });
});
