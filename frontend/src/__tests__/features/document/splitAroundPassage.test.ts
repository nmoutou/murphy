import { describe, expect, it } from 'vitest';
import { splitAroundPassage } from '@/features/document/splitAroundPassage';

const CONTENT = 'Les actions se prescrivent par cinq ans.';

describe('splitAroundPassage', () => {
  it('cuts the text around the passage', () => {
    expect(splitAroundPassage(CONTENT, { start: 4, end: 11 })).toEqual({
      before: 'Les ',
      passage: 'actions',
      after: ' se prescrivent par cinq ans.',
    });
  });

  it('keeps a passage that ends the text', () => {
    expect(splitAroundPassage(CONTENT, { start: 31, end: CONTENT.length })).toEqual({
      before: 'Les actions se prescrivent par ',
      passage: 'cinq ans.',
      after: '',
    });
  });

  it.each([
    ['no passage', undefined],
    ['a passage past the end of the text', { start: 4, end: CONTENT.length + 1 }],
    ['an empty passage', { start: 4, end: 4 }],
    ['reversed offsets', { start: 11, end: 4 }],
  ])('leaves the text whole with %s', (_case, span) => {
    expect(splitAroundPassage(CONTENT, span)).toEqual({ before: CONTENT, passage: '', after: '' });
  });
});
