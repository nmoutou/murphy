'use client';

import type { SelectionEntry } from '@/stores/selectionStore';
import { useSelectionStore } from '@/stores/selectionStore';
import { useSearchStore } from '@/stores/searchStore';
import { askQuestion, stopAnswer, useExplanation } from '@/stores/explanationStore';
import { canExplain, isOverBudget } from '@/lib/selectionBudget';
import MessageList from './MessageList';
import QuestionForm from './QuestionForm';

const EMPTY_SELECTION_HINT =
  'Ajoutez des documents à la sélection depuis la recherche : il n’y a rien à expliquer sans eux.';
const OVER_BUDGET_HINT = 'La sélection dépasse le budget de lecture : retirez un document.';
const EMPTY_CONVERSATION =
  'Posez une question sur les documents sélectionnés, ou demandez-en un résumé depuis la sélection.';

const useQuestionHint = (): { readonly canAsk: boolean; readonly hint?: string } => {
  const entries = useSelectionStore((state) => state.entries);
  const budget = useSearchStore((state) => state.contextBudget);
  if (entries.length === 0) return { canAsk: false, hint: EMPTY_SELECTION_HINT };
  if (budget !== undefined && isOverBudget(entries, budget)) {
    return { canAsk: false, hint: OVER_BUDGET_HINT };
  }
  return { canAsk: canExplain(entries, budget) };
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
    <section className="flex h-full flex-col text-tertiary">
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4 scrollbar">
        {messages.length === 0 ? (
          <p className="text-sm">{EMPTY_CONVERSATION}</p>
        ) : (
          <MessageList messages={messages} onOpenDocument={onOpenDocument} />
        )}
      </div>
      <QuestionForm
        canAsk={canAsk}
        isAnswering={isAnswering}
        hint={hint}
        onAsk={(question) => void askQuestion(question)}
        onStop={() => void stopAnswer()}
      />
    </section>
  );
}
