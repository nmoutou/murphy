import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ChatBox from '@/components/ChatBox';

const QUESTION = 'Quel délai de prescription ?';

const renderChatBox = (disabled = false) => {
  const onEnter = vi.fn();
  const onCancel = vi.fn();
  const view = render(
    <ChatBox onEnter={onEnter} onCancel={onCancel} disabled={disabled} isDocked={false} />,
  );
  return {
    ...view,
    onEnter,
    onCancel,
    field: screen.getByRole('textbox', { name: 'Votre question' }),
  };
};

const formOf = (element: HTMLElement): HTMLFormElement => {
  const form = element.closest('form');
  if (!form) throw new Error('The question field is outside any form');
  return form;
};

describe('ChatBox', () => {
  it('sends the question on Enter, then empties the field', async () => {
    const { field, onEnter } = renderChatBox();

    await userEvent.type(field, `${QUESTION}{Enter}`);

    expect(onEnter).toHaveBeenCalledExactlyOnceWith(QUESTION);
    expect(field).toHaveValue('');
  });

  it('sends the question from the send button', async () => {
    const { field, onEnter } = renderChatBox();

    await userEvent.type(field, QUESTION);
    await userEvent.click(screen.getByRole('button', { name: 'Envoyer la question' }));

    expect(onEnter).toHaveBeenCalledExactlyOnceWith(QUESTION);
  });

  it.each([
    ['an empty field', '{Enter}'],
    ['a blank field', '   {Enter}'],
  ])('sends nothing from %s', async (_case, keys) => {
    const { field, onEnter } = renderChatBox();

    await userEvent.type(field, keys);

    expect(onEnter).not.toHaveBeenCalled();
  });

  it('offers to cancel while an answer streams, instead of sending', async () => {
    const { field, onCancel } = renderChatBox(true);

    expect(field).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Envoyer la question' })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Annuler' }));

    expect(onCancel).toHaveBeenCalledOnce();
  });

  it('keeps a question typed before the stream, without sending it', async () => {
    const { field, onEnter, rerender } = renderChatBox();
    await userEvent.type(field, QUESTION);

    rerender(<ChatBox onEnter={onEnter} disabled isDocked />);
    fireEvent.submit(formOf(field));

    expect(onEnter).not.toHaveBeenCalled();
    expect(field).toHaveValue(QUESTION);
  });
});
