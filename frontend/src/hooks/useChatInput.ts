import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';

interface ChatInputOptions {
  readonly onEnter: (content: string) => void;
  readonly disabled: boolean;
}

/** The question being typed: sent on submit unless blank or while a stream runs */
export function useChatInput({ onEnter, disabled }: ChatInputOptions) {
  const [content, setContent] = useState('');

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => setContent(event.target.value);

  // Enter in the field submits the form natively, NumpadEnter included
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (disabled || !content.trim()) return;
    onEnter(content);
    setContent('');
  };

  return { content, handleChange, handleSubmit };
}
