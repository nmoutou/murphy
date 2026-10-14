import type { RefObject } from 'react';
import { useEffect } from 'react';
import type { ExplanationUIMessage } from '@/lib/api/explanationRequest';

// Posé par UserMessage
const QUESTION_SELECTOR = '[data-question]';

const findLastQuestion = (panel: HTMLElement): Element | undefined => {
  const questions = panel.querySelectorAll(QUESTION_SELECTOR);
  return questions[questions.length - 1];
};

/** Chaque question envoyée remonte en haut du panneau ; la réponse s'écrit dessous */
export const useScrollToLastQuestion = (
  panelRef: RefObject<HTMLElement | null>,
  messages: readonly ExplanationUIMessage[],
): void => {
  const lastQuestionId = messages.findLast((message) => message.role === 'user')?.id;

  useEffect(() => {
    const panel = panelRef.current;
    const question = panel && lastQuestionId !== undefined ? findLastQuestion(panel) : undefined;
    if (!panel || !question) return;
    // scrollIntoView ferait aussi défiler les conteneurs de Dockview
    const offset = question.getBoundingClientRect().top - panel.getBoundingClientRect().top;
    const paddingTop = Number.parseFloat(getComputedStyle(panel).paddingTop);
    panel.scrollTo({ top: panel.scrollTop + offset - paddingTop, behavior: 'smooth' });
  }, [panelRef, lastQuestionId]);
};
