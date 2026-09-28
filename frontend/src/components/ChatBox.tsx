import AnimatedButtonIcon from './icons/AnimatedButtonIcon';
import ButtonIcon from './icons/ButtonIcon';
import { useChatInput } from '@/hooks/useChatInput';

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

interface ChatBoxActionProps {
  readonly isStreaming: boolean;
  readonly onCancel?: () => void;
}

interface ChatBoxAttachProps {
  readonly isStreaming: boolean;
}

/** Attaching a document is not built yet; the button is inert while an answer streams */
function ChatBoxAttach({ isStreaming }: ChatBoxAttachProps) {
  const pointerClasses = isStreaming ? 'pointer-events-none' : 'pointer-events-auto';
  return (
    <div className={pointerClasses}>
      <AnimatedButtonIcon
        icon="folder"
        size={ICON_SIZE}
        label="Joindre un document"
        onClick={() => alert(WORK_IN_PROGRESS)}
      />
    </div>
  );
}

/** Stop while an answer streams, send otherwise */
function ChatBoxAction({ isStreaming, onCancel }: ChatBoxActionProps) {
  if (isStreaming) {
    return (
      <ButtonIcon
        icon="stop"
        label="Annuler"
        size={ICON_SIZE}
        onClick={onCancel}
        variant="primary"
      />
    );
  }
  return (
    <AnimatedButtonIcon
      icon="globe"
      label="Envoyer la question"
      size={ICON_SIZE}
      type="submit"
      variant="primary"
    />
  );
}

export default function ChatBox({ onEnter, onCancel, disabled = false, isDocked }: ChatBoxProps) {
  const { content, handleChange, handleSubmit } = useChatInput({ onEnter, disabled });

  const dockClasses = isDocked ? 'fixed bottom-0 my-4' : '';

  return (
    <form
      onSubmit={handleSubmit}
      className={`flex justify-center items-center p-3 rounded-[25px] gap-2 mx-8 w-full max-w-[600px] bg-secondary ${dockClasses}`}
    >
      <ChatBoxAttach isStreaming={disabled} />

      <input
        name="chatbox"
        aria-label="Votre question"
        className="h-full w-full text-tertiary focus:outline-none placeholder:italic placeholder:text-center truncate disabled:opacity-50"
        placeholder={DEFAULT_PLACEHOLDER}
        onChange={handleChange}
        value={content}
        disabled={disabled}
        autoComplete="off"
      />

      <ChatBoxAction isStreaming={disabled} onCancel={onCancel} />
    </form>
  );
}
