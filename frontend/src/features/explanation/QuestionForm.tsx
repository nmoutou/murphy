'use client';

import { useQuestionInput } from './useQuestionInput';

interface QuestionFormProps {
  /** Faux sans sélection ou au-delà du budget : le champ est alors désactivé */
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
    <form onSubmit={handleSubmit} className="flex flex-col gap-1 border-t border-secondary p-3">
      {hint && <p className="text-sm">{hint}</p>}
      <div className="flex items-end gap-2">
        <textarea
          aria-label="Votre question sur les documents"
          value={question}
          disabled={!canAsk}
          rows={2}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={handleKeyDown}
          className="min-h-0 flex-1 resize-none rounded-lg bg-secondary px-3 py-2 text-quaternary outline-none disabled:opacity-40"
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

function SubmitOrStop({ isAnswering, canSend, onStop }: SubmitOrStopProps) {
  const style = 'rounded-full px-4 py-1 hover:opacity-80 disabled:opacity-40';
  if (isAnswering) {
    return (
      <button type="button" onClick={onStop} className={`${style} bg-not-in-force text-primary`}>
        Arrêter
      </button>
    );
  }
  return (
    <button type="submit" disabled={!canSend} className={`${style} bg-quaternary text-primary`}>
      Envoyer
    </button>
  );
}
