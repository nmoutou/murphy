/**
 * Source Item Tests
 * A retrieved passage, shown with its document type and, when meaningful, its legal nature
 */

import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { DocumentChunk } from '@murphy/contract/messages';
import SourceItem from '@/components/chat/SourceItem';

const CHUNK: DocumentChunk = {
  chunkId: 'LEGITEXT000006069577_0001',
  identifier: 'LEGITEXT000006069577',
  highlightStart: 0,
  highlightEnd: 12,
  score: 0.8,
  title: 'Loi du 29 juillet 1881',
  documentType: 'texte',
};

describe('SourceItem', () => {
  it.each<[Partial<DocumentChunk>, string]>([
    [{ nature: 'LOI' }, 'Texte · LOI'],
    [{}, 'Texte'],
    [{ documentType: 'decision', nature: 'QPC' }, 'Décision · QPC'],
  ])('names the document type and its nature (%o)', (overrides, label) => {
    render(<SourceItem chunk={{ ...CHUNK, ...overrides }} />);

    expect(screen.getByText(label)).toBeInTheDocument();
  });
});
