import { useState } from 'react';
import type { FormEvent } from 'react';
import AnimatedButtonIcon from './icons/AnimatedButtonIcon';
import ButtonIcon from './icons/ButtonIcon';

const DEFAULT_PLACEHOLDER = "Nul n'est censé ignorer la loi.";
const WORK_IN_PROGRESS = 'Work in progress !';
const ICON_SIZE = 32;

interface ChatBoxProps {
  readonly onEnter: (content: string) => void;
  readonly onCancel?: () => void;
  readonly disabled?: boolean;
  /** Pinned to the bottom of the page, once the conversation has started */
  readonly isDocked: boolean;
}

export default function ChatBox({ onEnter, onCancel, disabled = false, isDocked }: ChatBoxProps) {
  const [content, setContent] = useState('');

  // Enter in the field submits the form natively, NumpadEnter included
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (disabled || !content.trim()) return;
    onEnter(content);
    setContent('');
  };

  const dockClasses = isDocked ? 'fixed bottom-0 my-4' : '';
  const attachClasses = disabled ? 'pointer-events-none' : 'pointer-events-auto';

  return (
    <form
      onSubmit={handleSubmit}
      className={`flex justify-center items-center p-3 rounded-[25px] gap-2 mx-8 w-full max-w-[600px] bg-secondary ${dockClasses}`}
    >
      <div className={attachClasses}>
        <AnimatedButtonIcon
          icon="folder"
          size={ICON_SIZE}
          label="Joindre un document"
          onClick={() => alert(WORK_IN_PROGRESS)}
        />
      </div>

      <input
        name="chatbox"
        aria-label="Votre question"
        className="h-full w-full text-tertiary focus:outline-none placeholder:italic placeholder:text-center truncate disabled:opacity-50"
        placeholder={DEFAULT_PLACEHOLDER}
        onChange={(event) => setContent(event.target.value)}
        value={content}
        disabled={disabled}
        autoComplete="off"
      />

      {disabled ? (
        <ButtonIcon
          icon="stop"
          label="Annuler"
          size={ICON_SIZE}
          onClick={onCancel}
          variant="primary"
        />
      ) : (
        <AnimatedButtonIcon
          icon="globe"
          label="Envoyer la question"
          size={ICON_SIZE}
          type="submit"
          variant="primary"
        />
      )}
    </form>
  );
}
