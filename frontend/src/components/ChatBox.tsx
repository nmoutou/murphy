import AnimatedButtonIcon from './icons/AnimatedButtonIcon';
import ButtonIcon from './icons/ButtonIcon';
import { useState, useEffect, useCallback } from 'react';

const DEFAULT_PLACEHOLDER = "Nul n'est censé ignorer la loi.";

interface ChatBoxProps {
  onEnter: (content: string) => void;
  onCancel?: () => void;
  disabled?: boolean;
  absolute: boolean;
}

export default function ChatBox({ onEnter, onCancel, disabled = false, absolute }: ChatBoxProps) {
  const [content, setContent] = useState('');

  const launchSearch = useCallback(() => {
    if (content && !disabled) {
      onEnter(content);
      setContent('');
    }
  }, [content, onEnter, disabled]);

  useEffect(() => {
    function keyOnHandler(e: KeyboardEvent) {
      if (e.code == 'Enter') {
        launchSearch();
      }
    }

    document.addEventListener('keydown', keyOnHandler);

    return function () {
      document.removeEventListener('keydown', keyOnHandler);
    };
  }, [launchSearch]);

  return (
    <div
      className={`flex justify-center items-center p-3 rounded-[25px] gap-2 mx-8 w-full max-w-[600px] bg-secondary ${absolute ? 'fixed bottom-0 my-4' : ''}`}
    >
      <div className={disabled ? 'pointer-events-none' : 'pointer-events-auto'}>
        <AnimatedButtonIcon
          icon="folder"
          size={32}
          alt="Folder icon"
          onClick={() => {
            alert('Work in progress !');
          }}
        />
      </div>

      <input
        name="chatbox"
        className="h-full w-full text-tertiary focus:outline-none placeholder:italic placeholder:text-center truncate disabled:opacity-50"
        placeholder={DEFAULT_PLACEHOLDER}
        onChange={(event) => {
          setContent(event.target.value);
        }}
        value={content}
        disabled={disabled}
        autoComplete="off"
      />

      {!disabled ? (
        <AnimatedButtonIcon
          icon="globe"
          size={32}
          alt="Globe icon"
          onClick={() => {
            launchSearch();
          }}
          variant="primary"
        />
      ) : (
        <ButtonIcon
          icon="stop"
          alt="Annuler"
          size={32}
          onClick={() => {
            onCancel?.();
          }}
          variant="primary"
        />
      )}
    </div>
  );
}
