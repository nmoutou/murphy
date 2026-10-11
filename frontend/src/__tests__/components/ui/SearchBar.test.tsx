import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SearchBar from '@/components/ui/SearchBar';

const QUESTION = 'Quel délai de prescription ?';

const renderSearchBar = (initialQuestion?: string) => {
  const onSubmit = vi.fn();
  render(<SearchBar variant="centered" onSubmit={onSubmit} initialQuestion={initialQuestion} />);
  return { onSubmit, field: screen.getByRole('textbox', { name: 'Votre question' }) };
};

describe('SearchBar', () => {
  it('sends the question on Enter, and keeps it in the field', async () => {
    const { field, onSubmit } = renderSearchBar();

    await userEvent.type(field, `${QUESTION}{Enter}`);

    expect(onSubmit).toHaveBeenCalledExactlyOnceWith(QUESTION);
    expect(field).toHaveValue(QUESTION);
  });

  it('sends the question from the button', async () => {
    const { field, onSubmit } = renderSearchBar();

    await userEvent.type(field, QUESTION);
    await userEvent.click(screen.getByRole('button', { name: 'Lancer la recherche' }));

    expect(onSubmit).toHaveBeenCalledExactlyOnceWith(QUESTION);
  });

  it.each([
    ['an empty field', '{Enter}'],
    ['a blank field', '   {Enter}'],
  ])('sends nothing from %s', async (_case, keys) => {
    const { field, onSubmit } = renderSearchBar();

    await userEvent.type(field, keys);

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('starts from the question it is given', () => {
    const { field } = renderSearchBar(QUESTION);

    expect(field).toHaveValue(QUESTION);
  });
});
