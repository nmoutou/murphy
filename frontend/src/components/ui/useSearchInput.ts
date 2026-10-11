import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';

/** La question reste dans le champ après l'envoi : elle se corrige sans être retapée */
export const useSearchInput = (onSubmit: (question: string) => void, initialQuestion: string) => {
  const [question, setQuestion] = useState(initialQuestion);

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => setQuestion(event.target.value);

  // Entrée soumet le formulaire nativement, NumpadEnter compris
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (question.trim()) onSubmit(question);
  };

  return { question, handleChange, handleSubmit };
};
