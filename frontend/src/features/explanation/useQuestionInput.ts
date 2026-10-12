import { useState } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';

interface QuestionInput {
  readonly question: string;
  readonly canSend: boolean;
  readonly setQuestion: (question: string) => void;
  readonly handleSubmit: (event: FormEvent<HTMLFormElement>) => void;
  readonly handleKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
}

/** Entrée envoie, Maj+Entrée va à la ligne ; une question envoyée vide le champ */
export const useQuestionInput = (
  canAsk: boolean,
  onAsk: (question: string) => void,
): QuestionInput => {
  const [question, setQuestion] = useState('');
  const trimmed = question.trim();
  const canSend = canAsk && trimmed !== '';

  const send = () => {
    if (!canSend) return;
    onAsk(trimmed);
    setQuestion('');
  };

  return {
    question,
    canSend,
    setQuestion,
    handleSubmit: (event) => {
      event.preventDefault();
      send();
    },
    handleKeyDown: (event) => {
      if (event.key !== 'Enter' || event.shiftKey) return;
      event.preventDefault();
      send();
    },
  };
};
