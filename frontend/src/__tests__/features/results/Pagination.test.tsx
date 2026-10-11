import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Pagination from '@/features/results/Pagination';

const renderPagination = (page: number, pageCount: number) => {
  const onGoToPage = vi.fn();
  render(<Pagination page={page} pageCount={pageCount} onGoToPage={onGoToPage} />);
  return onGoToPage;
};

describe('Pagination', () => {
  it('marks the current page', () => {
    renderPagination(5, 10);

    expect(screen.getByRole('button', { name: 'Page 5' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('button', { name: 'Page 4' })).not.toHaveAttribute('aria-current');
  });

  it.each([
    ['Première page', 1],
    ['Page précédente', 4],
    ['Page 6', 6],
    ['Page suivante', 6],
    ['Dernière page', 10],
  ])('%s goes to page %i', async (label, expected) => {
    const onGoToPage = renderPagination(5, 10);

    await userEvent.click(screen.getByRole('button', { name: label }));

    expect(onGoToPage).toHaveBeenCalledExactlyOnceWith(expected);
  });

  it('disables going back from the first page', () => {
    renderPagination(1, 10);

    expect(screen.getByRole('button', { name: 'Première page' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Page précédente' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Page suivante' })).toBeEnabled();
  });

  it('disables going forward from the last page', () => {
    renderPagination(10, 10);

    expect(screen.getByRole('button', { name: 'Page suivante' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Dernière page' })).toBeDisabled();
  });
});
