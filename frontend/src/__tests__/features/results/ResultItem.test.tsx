import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { SearchResult } from '@murphy/contract/search';
import ResultItem from '@/features/results/ResultItem';

const RESULT: SearchResult = {
  identifier: 'LEGIARTI000032040843',
  title: 'Article 2224',
  documentType: 'article',
  isInForce: true,
  passages: [
    {
      chunkId: 'c1',
      text: 'Les actions personnelles se prescrivent par cinq ans.',
      start: 0,
      end: 52,
    },
    { chunkId: 'c2', text: 'Un passage moins bien classé.', start: 60, end: 89 },
  ],
};

const renderItem = (result: SearchResult, onOpenDocument = vi.fn()) =>
  render(
    <ul>
      <ResultItem result={result} onOpenDocument={onOpenDocument} />
    </ul>,
  );

describe('ResultItem', () => {
  it.each([
    [true, 'En vigueur'],
    [false, 'Pas en vigueur'],
  ])('shows the dot of isInForce = %s', (isInForce, label) => {
    renderItem({ ...RESULT, isInForce });

    expect(screen.getByRole('img', { name: label })).toBeInTheDocument();
  });

  it('shows no dot without a status', () => {
    renderItem({ ...RESULT, isInForce: undefined });

    expect(screen.queryByRole('img', { name: /en vigueur/i })).not.toBeInTheDocument();
  });

  it('shows the first passage only', () => {
    renderItem(RESULT);

    expect(screen.getByText(/se prescrivent par cinq ans/)).toBeInTheDocument();
    expect(screen.queryByText('Un passage moins bien classé.')).not.toBeInTheDocument();
  });

  it('shows the title alone without a passage', () => {
    renderItem({ ...RESULT, passages: [] });

    expect(screen.getByRole('article')).toHaveTextContent(/^Article 2224$/);
  });

  it('opens the document from its title', async () => {
    const onOpenDocument = vi.fn();
    renderItem(RESULT, onOpenDocument);

    await userEvent.click(screen.getByRole('button', { name: 'Article 2224' }));

    expect(onOpenDocument).toHaveBeenCalledExactlyOnceWith(RESULT);
  });

  it('has a menu with no option yet', () => {
    renderItem(RESULT);

    expect(screen.getByRole('button', { name: 'Options de Article 2224' })).toBeDisabled();
  });
});
