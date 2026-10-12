import { describe, expect, it } from 'vitest';
import { linkCitations, readCitation } from '@/features/explanation/citations';

describe('linkCitations', () => {
  it('links every reference, side by side or apart', () => {
    expect(linkCitations('Selon [1] et [2][3].')).toBe(
      'Selon [1](#source-1) et [2](#source-2)[3](#source-3).',
    );
  });

  it('leaves a Markdown link and a bracket without a number alone', () => {
    expect(linkCitations('[1](https://x.test) [note]')).toBe('[1](https://x.test) [note]');
  });
});

describe('readCitation', () => {
  it('reads the number of a linked reference only', () => {
    expect(readCitation('#source-12')).toBe(12);
    expect(readCitation('https://x.test')).toBeUndefined();
    expect(readCitation(undefined)).toBeUndefined();
  });
});
