'use client';

import type { SelectionEntry } from '@/stores/selectionStore';
import { useSelectionStore } from '@/stores/selectionStore';
import { useSearchStore } from '@/stores/searchStore';
import { askQuestion, stopAnswer, useExplanation } from '@/stores/explanationStore';
import { isOverBudget } from '@/lib/selectionBudget';
import MessageList from './MessageList';
import QuestionForm from './QuestionForm';

const OVER_BUDGET_HINT = 'La sélection dépasse le budget de lecture : retirez un document.';
const EMPTY_CONVERSATION =
  'Posez une question sur les documents sélectionnés, ou demandez-en un résumé depuis la sélection.';

const useQuestionHint = (): { readonly canAsk: boolean; readonly hint?: string } => {
  const entries = useSelectionStore((state) => state.entries);
  const budget = useSearchStore((state) => state.contextBudget);
  if (budget !== undefined && isOverBudget(entries, budget)) {
    return { canAsk: false, hint: OVER_BUDGET_HINT };
  }
  // Sans document aussi : le LLM invite alors à en choisir
  return { canAsk: true };
};

interface ExplanationPanelProps {
  readonly onOpenDocument: (source: SelectionEntry) => void;
}

/** Le LLM résume et explique les documents choisis, rien d'autre (ADR-033) */
export default function ExplanationPanel({ onOpenDocument }: ExplanationPanelProps) {
  const { messages, status } = useExplanation();
  const { canAsk, hint } = useQuestionHint();
  const isAnswering = status === 'submitted' || status === 'streaming';

  return (
    // pb-6 = bottom-6 du champ : tout en bas, le texte finit au-dessus de lui
    <section className="flex h-full flex-col overflow-y-auto px-4 pt-4 pb-2 text-tertiary scrollbar">
      <div className="flex-1">
        {messages.length === 0 ? (
          <p className="text-sm">{EMPTY_CONVERSATION}</p>
        ) : (
          <MessageList messages={messages} onOpenDocument={onOpenDocument} />
        )}
      </div>
      <div className="sticky bottom-2 mt-6">
        <QuestionForm
          canAsk={canAsk}
          isAnswering={isAnswering}
          hint={hint}
          onAsk={(question) => void askQuestion(question)}
          onStop={() => void stopAnswer()}
        />
      </div>
    </section>
  );
}
