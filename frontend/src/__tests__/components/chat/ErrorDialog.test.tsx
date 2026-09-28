/**
 * Error Dialog Tests
 * The modal that names the failed stage (ADR-041), closed by its button or by Escape
 */

import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ErrorDialog from '@/components/chat/ErrorDialog';
import type { DisplayedErrorStage } from '@/lib/chatErrorStage';

const TITLE = 'Une erreur est survenue';
const RETRY_HINT = 'Vous pouvez reposer votre question dans un instant.';

const renderDialog = (stage: DisplayedErrorStage = 'llm') => {
  const onClose = vi.fn();
  const view = render(<ErrorDialog stage={stage} onClose={onClose} />);
  return { ...view, onClose, dialog: screen.getByRole('dialog', { name: TITLE }) };
};

describe('ErrorDialog', () => {
  it.each<[DisplayedErrorStage, string]>([
    ['request', "Votre question n'a pas pu être traitée."],
    ['embedding', "L'encodage de votre question a échoué."],
    ['retrieval', 'La recherche des sources a échoué.'],
    ['llm', 'La rédaction de la réponse a échoué.'],
    ['internal', 'Une erreur interne est survenue.'],
    ['connection', 'Le serveur est injoignable.'],
  ])('opens on the %s stage, named by its title, with the retry hint', (stage, message) => {
    const { dialog } = renderDialog(stage);

    expect(dialog).toHaveAttribute('open');
    expect(dialog).toHaveTextContent(`${message} ${RETRY_HINT}`);
  });

  it('asks its parent to close it from the button', async () => {
    const { onClose } = renderDialog();

    await userEvent.click(screen.getByRole('button', { name: 'Fermer' }));

    expect(onClose).toHaveBeenCalledOnce();
  });

  it('routes Escape to its parent instead of closing itself', () => {
    const { dialog, onClose } = renderDialog();
    const escape = new Event('cancel', { cancelable: true });

    fireEvent(dialog, escape);

    expect(escape.defaultPrevented).toBe(true);
    expect(onClose).toHaveBeenCalledOnce();
    expect(dialog).toHaveAttribute('open');
  });

  it('closes the native dialog once its parent unmounts it', () => {
    const { dialog, unmount } = renderDialog();

    unmount();

    expect(dialog).not.toHaveAttribute('open');
  });
});
