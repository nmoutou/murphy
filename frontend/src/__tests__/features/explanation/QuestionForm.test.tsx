import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import QuestionForm from '@/features/explanation/QuestionForm';

const FIELD = 'Votre question sur les documents';

const renderForm = ({
  canAsk = true,
  isAnswering = false,
  hint = undefined as string | undefined,
} = {}) => {
  const onAsk = vi.fn();
  const onStop = vi.fn();
  render(
    <QuestionForm
      canAsk={canAsk}
      isAnswering={isAnswering}
      hint={hint}
      onAsk={onAsk}
      onStop={onStop}
    />,
  );
  return { onAsk, onStop };
};

describe('QuestionForm', () => {
  it('sends the question with Enter, trimmed, then empties the field', async () => {
    const { onAsk } = renderForm();

    await userEvent.type(screen.getByRole('textbox', { name: FIELD }), '  Que dit [[1] ?  {Enter}');

    expect(onAsk).toHaveBeenCalledExactlyOnceWith('Que dit [1] ?');
    expect(screen.getByRole('textbox', { name: FIELD })).toHaveValue('');
  });

  it('goes to the line with Shift+Enter', async () => {
    const { onAsk } = renderForm();

    await userEvent.type(
      screen.getByRole('textbox', { name: FIELD }),
      'Un{Shift>}{Enter}{/Shift}deux',
    );

    expect(onAsk).not.toHaveBeenCalled();
    expect(screen.getByRole('textbox', { name: FIELD })).toHaveValue('Un\ndeux');
  });

  it('is disabled, saying why, when the selection cannot be explained', () => {
    renderForm({ canAsk: false, hint: 'Ajoutez des documents.' });

    expect(screen.getByRole('textbox', { name: FIELD })).toBeDisabled();
    expect(screen.getByText('Ajoutez des documents.')).toBeInTheDocument();
  });

  it('offers to stop an answer, and keeps the field open meanwhile', async () => {
    const { onAsk, onStop } = renderForm({ isAnswering: true });

    await userEvent.type(screen.getByRole('textbox', { name: FIELD }), 'Suite ?{Enter}');
    await userEvent.click(screen.getByRole('button', { name: 'Arrêter' }));

    expect(onAsk).not.toHaveBeenCalled();
    expect(onStop).toHaveBeenCalledOnce();
  });
});
