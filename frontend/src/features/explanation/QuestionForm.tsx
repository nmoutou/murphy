'use client';

import AnimatedButtonIcon from '@/components/icons/AnimatedButtonIcon';
import ButtonIcon from '@/components/icons/ButtonIcon';
import { useQuestionInput } from './useQuestionInput';

const ICON_SIZE = 24;

interface QuestionFormProps {
  /** Faux au-delà du budget : on peut écrire, pas envoyer */
  readonly canAsk: boolean;
  /** Le champ reste ouvert pendant une réponse ; seul l'envoi attend */
  readonly isAnswering: boolean;
  /** Pourquoi la question ne peut pas partir, quand elle ne le peut pas */
  readonly hint?: string;
  readonly onAsk: (question: string) => void;
  readonly onStop: () => void;
}

export default function QuestionForm({
  canAsk,
  isAnswering,
  hint,
  onAsk,
  onStop,
}: QuestionFormProps) {
  const { question, canSend, setQuestion, handleSubmit, handleKeyDown } = useQuestionInput(
    canAsk && !isAnswering,
    onAsk,
  );

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-1">
      {hint && <p className="self-start rounded-xl bg-secondary px-3 py-1 text-sm">{hint}</p>}
      <div className="flex items-end gap-2 rounded-[25px] bg-secondary px-3 py-1">
        <textarea
          aria-label="Votre question sur les documents"
          value={question}
          rows={1}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={handleKeyDown}
          className="field-sizing-content max-h-40 min-w-0 flex-1 resize-none self-center bg-transparent px-2 py-1 font-mono text-tertiary focus:outline-none scrollbar"
        />
        <SubmitOrStop isAnswering={isAnswering} canSend={canSend} onStop={onStop} />
      </div>
    </form>
  );
}

interface SubmitOrStopProps {
  readonly isAnswering: boolean;
  readonly canSend: boolean;
  readonly onStop: () => void;
}

/** L'icône d'arrêt n'a pas de version animée */
function SubmitOrStop({ isAnswering, canSend, onStop }: SubmitOrStopProps) {
  if (isAnswering) {
    return (
      <ButtonIcon icon="stop" label="Arrêter" size={ICON_SIZE} variant="primary" onClick={onStop} />
    );
  }
  return (
    <AnimatedButtonIcon
      icon="globe"
      label="Envoyer"
      size={ICON_SIZE}
      type="submit"
      variant="primary"
      disabled={!canSend}
    />
  );
}
