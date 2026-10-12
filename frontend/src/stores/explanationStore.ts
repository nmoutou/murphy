import { Chat, useChat } from '@ai-sdk/react';
import type { UseChatHelpers } from '@ai-sdk/react';
import type { ExplanationUIMessage } from '@/lib/api/explanationRequest';
import { reportApiError } from '@/lib/api/apiError';
import { createExplanationTransport } from '@/lib/api/explanations';
import { useErrorStore } from './errorStore';
import { useSelectionStore } from './selectionStore';

/** Le message du bouton « Résumer » : le backend le traite comme toute autre question */
export const SUMMARY_REQUEST = 'Veuillez résumer les documents fournis.';

interface FinishedAnswer {
  readonly message: ExplanationUIMessage;
  readonly isAbort: boolean;
  readonly isError: boolean;
}

/** Arrêtée, la réponse reste, marquée ; en erreur, elle part, et la question reste */
const settleAnswer = (
  chat: Chat<ExplanationUIMessage>,
  { message, isAbort, isError }: FinishedAnswer,
) => {
  if (isError) {
    chat.messages = chat.messages.filter((candidate) => candidate.id !== message.id);
  } else if (isAbort) {
    chat.messages = chat.messages.map((candidate) =>
      candidate.id === message.id
        ? { ...candidate, metadata: { sources: [], ...candidate.metadata, isInterrupted: true } }
        : candidate,
    );
  }
};

/**
 * Hors du panneau : fermer l'onglet ne perd pas la conversation, et la sidebar peut y
 * écrire. Elle disparaît au rechargement.
 */
export const explanationChat: Chat<ExplanationUIMessage> = new Chat<ExplanationUIMessage>({
  transport: createExplanationTransport(),
  onError: (error) => useErrorStore.getState().showError(reportApiError(error)),
  onFinish: (finished) => settleAnswer(explanationChat, finished),
});

/** La question part avec la sélection du moment, que le message garde */
export const askQuestion = (text: string): Promise<void> =>
  explanationChat.sendMessage({
    text,
    metadata: { sources: [...useSelectionStore.getState().entries] },
  });

export const summarize = (): Promise<void> => askQuestion(SUMMARY_REQUEST);

export const stopAnswer = (): Promise<void> => explanationChat.stop();

export const useExplanation = (): UseChatHelpers<ExplanationUIMessage> =>
  useChat({ chat: explanationChat });

export const useIsAnswering = (): boolean => {
  const { status } = useExplanation();
  return status === 'submitted' || status === 'streaming';
};
