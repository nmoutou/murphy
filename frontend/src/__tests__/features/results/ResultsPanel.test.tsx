import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { SearchRequest, SearchResponse } from '@murphy/contract/search';
import ResultsPanel from '@/features/results/ResultsPanel';
import { searchDocuments } from '@/lib/api/search';
import { useSearchStore } from '@/stores/searchStore';

vi.mock('@/lib/api/search', () => ({ searchDocuments: vi.fn() }));

const searchMock = vi.mocked(searchDocuments);

const responseFor = ({ page }: SearchRequest): SearchResponse => ({
  page,
  pageCount: 10,
  pageSize: 10,
  pageSizes: [10, 25, 50],
  results: [
    {
      identifier: `first-${page}`,
      title: `Premier de la page ${page}`,
      documentType: 'article',
      passages: [],
    },
    {
      identifier: `second-${page}`,
      title: `Second de la page ${page}`,
      documentType: 'decision',
      passages: [],
    },
  ],
});

const submit = () => act(() => useSearchStore.getState().submit('Quel délai ?'));

beforeEach(() => {
  searchMock.mockReset();
  searchMock.mockImplementation((request) => Promise.resolve(responseFor(request)));
  useSearchStore.setState(useSearchStore.getInitialState(), true);
});

describe('ResultsPanel', () => {
  it('lists the results in ranking order', async () => {
    render(<ResultsPanel onOpenDocument={vi.fn()} />);

    await submit();

    const titles = within(screen.getByRole('list', { name: 'Résultats' }))
      .getAllByRole('listitem')
      .map((item) => within(item).getAllByRole('button')[1]?.textContent);
    expect(titles).toEqual(['Premier de la page 1', 'Second de la page 1']);
  });

  it('searches the page chosen in the pagination', async () => {
    render(<ResultsPanel onOpenDocument={vi.fn()} />);
    await submit();

    await userEvent.click(screen.getByRole('button', { name: 'Page suivante' }));

    expect(await screen.findByText('Premier de la page 2')).toBeInTheDocument();
    expect(searchMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 2 }),
      expect.anything(),
    );
  });

  it('keeps the pagination, on the requested page, while the page loads', async () => {
    render(<ResultsPanel onOpenDocument={vi.fn()} />);
    await submit();
    searchMock.mockReturnValue(new Promise(() => {}));

    await userEvent.click(screen.getByRole('button', { name: 'Page 2' }));

    expect(screen.getByRole('status')).toHaveTextContent('Recherche…');
    expect(screen.queryByRole('list', { name: 'Résultats' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Page 2' })).toHaveAttribute('aria-current', 'page');
  });

  it('shows no pagination before a response', () => {
    render(<ResultsPanel onOpenDocument={vi.fn()} />);

    expect(screen.queryByRole('navigation', { name: 'Pagination' })).not.toBeInTheDocument();
  });
});
