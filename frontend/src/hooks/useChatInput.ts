import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';

interface ChatInputOptions {
  readonly onEnter: (content: string) => void;
  readonly disabled: boolean;
}

/** Envoyée à la soumission, sauf si vide ou pendant une réponse */
export function useChatInput({ onEnter, disabled }: ChatInputOptions) {
  const [content, setContent] = useState('');

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => setContent(event.target.value);

  // Entrée soumet le formulaire nativement, NumpadEnter compris
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (disabled || !content.trim()) return;
    onEnter(content);
    setContent('');
  };

  return { content, handleChange, handleSubmit };
}
