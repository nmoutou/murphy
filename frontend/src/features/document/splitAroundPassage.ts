import type { Passage } from '@murphy/contract/search';

export type PassageSpan = Pick<Passage, 'start' | 'end'>;

export interface SplitContent {
  readonly before: string;
  readonly passage: string;
  readonly after: string;
}

const isWithin = (content: string, { start, end }: PassageSpan): boolean =>
  start < end && end <= content.length;

/** Des offsets hors du texte laissent le texte entier, sans surlignage */
export const splitAroundPassage = (content: string, span?: PassageSpan): SplitContent => {
  if (!span || !isWithin(content, span)) return { before: content, passage: '', after: '' };
  return {
    before: content.slice(0, span.start),
    passage: content.slice(span.start, span.end),
    after: content.slice(span.end),
  };
};
