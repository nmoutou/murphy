import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ApiError } from '@/lib/api/apiError';
import { searchDocuments } from '@/lib/api/search';
import SearchScreen from '@/features/workspace/SearchScreen';
import { useErrorStore } from '@/stores/errorStore';
import { useSearchStore } from '@/stores/searchStore';

vi.mock('@/lib/api/search', () => ({ searchDocuments: vi.fn() }));

const QUESTION = 'Quel délai de prescription ?';
const searchMock = vi.mocked(searchDocuments);

const search = async () => {
  await userEvent.type(
    screen.getByRole('textbox', { name: 'Votre question' }),
    `${QUESTION}{Enter}`,
  );
};

beforeEach(() => {
  searchMock.mockReset();
  useSearchStore.setState(useSearchStore.getInitialState(), true);
  useErrorStore.setState(useErrorStore.getInitialState(), true);
});

describe('SearchScreen', () => {
  it('shows the home screen before any search', () => {
    render(<SearchScreen />);

    expect(screen.getByRole('main')).toContainElement(screen.getByRole('search'));
  });

  it('opens the workspace on the first search, the question above the results', async () => {
    searchMock.mockResolvedValue({
      page: 1,
      pageCount: 10,
      pageSize: 10,
      pageSizes: [10],
      results: [],
    });
    render(<SearchScreen />);

    await search();

    expect(await screen.findByText('Aucun résultat.')).toBeInTheDocument();
    expect(screen.queryByRole('main')).not.toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Votre question' })).toHaveValue(QUESTION);
  });

  it('offers the page sizes after the first response, and searches again from page 1', async () => {
    searchMock.mockImplementation(({ page, pageSize = 10 }) =>
      Promise.resolve({ page, pageCount: 3, pageSize, pageSizes: [10, 25], results: [] }),
    );
    render(<SearchScreen />);
    await search();

    await userEvent.selectOptions(
      await screen.findByRole('combobox', { name: 'Résultats par page' }),
      '25',
    );

    expect(searchMock).toHaveBeenLastCalledWith(
      { question: QUESTION, page: 1, pageSize: 25 },
      expect.anything(),
    );
  });

  it('opens the workspace even when the first search fails, under the error', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    searchMock.mockRejectedValue(new ApiError('NETWORK', 'Failed to fetch'));
    render(<SearchScreen />);

    await search();

    expect(await screen.findByRole('dialog')).toHaveTextContent('Le serveur est injoignable.');
    expect(screen.queryByRole('main')).not.toBeInTheDocument();
  });
});
