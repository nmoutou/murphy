import { beforeEach, describe, expect, it } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ErrorDialog from '@/features/errors/ErrorDialog';
import type { DisplayedErrorCode } from '@/lib/api/apiError';
import { useErrorStore } from '@/stores/errorStore';

const TITLE = 'Une erreur est survenue';

const renderDialog = (code: DisplayedErrorCode = 'SEARCH_FAILED') => {
  useErrorStore.getState().showError(code);
  const view = render(<ErrorDialog />);
  return { ...view, dialog: screen.getByRole('dialog', { name: TITLE }) };
};

beforeEach(() => {
  useErrorStore.setState(useErrorStore.getInitialState(), true);
});

describe('ErrorDialog', () => {
  it('shows nothing without an error', () => {
    render(<ErrorDialog />);

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it.each<[DisplayedErrorCode, string]>([
    ['VALIDATION_ERROR', "La recherche n'a pas pu être lancée."],
    ['PAGE_OUT_OF_RANGE', "La recherche n'a pas pu être lancée."],
    ['SEARCH_RATE_LIMIT_EXCEEDED', 'Trop de recherches : réessayez dans une minute.'],
    ['DOCUMENT_NOT_FOUND', 'Ce document est introuvable.'],
    ['TIMEOUT', 'Le service de recherche est indisponible.'],
    ['CONTRACT_VIOLATION', 'Une erreur interne est survenue.'],
    ['NETWORK', 'Le serveur est injoignable.'],
  ])('opens on %s, named by its title, with its message', (code, message) => {
    const { dialog } = renderDialog(code);

    expect(dialog).toHaveAttribute('open');
    expect(dialog).toHaveTextContent(message);
  });

  it('clears the error from the button', async () => {
    renderDialog();

    await userEvent.click(screen.getByRole('button', { name: 'Fermer' }));

    expect(useErrorStore.getState().errorCode).toBeUndefined();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('clears the error on Escape instead of closing itself', () => {
    const { dialog } = renderDialog();
    const escape = new Event('cancel', { cancelable: true });

    act(() => {
      fireEvent(dialog, escape);
    });

    expect(escape.defaultPrevented).toBe(true);
    expect(useErrorStore.getState().errorCode).toBeUndefined();
  });

  it('closes the native dialog once the error is cleared', () => {
    const { dialog } = renderDialog();

    act(() => useErrorStore.getState().clearError());

    expect(dialog).not.toHaveAttribute('open');
  });
});
