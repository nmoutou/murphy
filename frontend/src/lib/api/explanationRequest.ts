import type { UIMessage } from 'ai';
import type { ExplanationMessage, ExplanationRequest } from '@murphy/contract/explanations';
import type { SelectionEntry } from '@/stores/selectionStore';

export interface ExplanationMetadata {
  /** La sélection au moment de la question : `[n]` dans la réponse désigne sa n-ième */
  readonly sources: readonly SelectionEntry[];
  /** Une réponse arrêtée par l'utilisateur, gardée telle quelle */
  readonly isInterrupted?: boolean;
}

/** Seul un message de l'utilisateur porte ses sources ; une réponse, au plus `isInterrupted` */
export type ExplanationUIMessage = UIMessage<ExplanationMetadata>;

export const textOf = (message: ExplanationUIMessage): string =>
  message.parts.map((part) => (part.type === 'text' ? part.text : '')).join('');

export const hasSameSources = (
  first: readonly SelectionEntry[],
  second: readonly SelectionEntry[],
): boolean =>
  first.length === second.length &&
  first.every((entry, index) => entry.identifier === second[index]?.identifier);

const sourcesOf = (message: ExplanationUIMessage): readonly SelectionEntry[] =>
  message.metadata?.sources ?? [];

/** Les sources d'un message : les siennes, ou celles de la question à laquelle il répond */
export const sourcesAt = (
  messages: readonly ExplanationUIMessage[],
  index: number,
): readonly SelectionEntry[] => {
  const question = messages.slice(0, index + 1).findLast((message) => message.role === 'user');
  return question ? sourcesOf(question) : [];
};

/** Un message de l'utilisateur ouvre un segment quand ses sources diffèrent des précédentes */
export const startsSegment = (
  messages: readonly ExplanationUIMessage[],
  index: number,
): boolean => {
  const message = messages[index];
  if (message?.role !== 'user') return false;
  const previous = messages.slice(0, index).findLast((candidate) => candidate.role === 'user');
  return previous !== undefined && !hasSameSources(sourcesOf(previous), sourcesOf(message));
};

const currentSegmentStart = (messages: readonly ExplanationUIMessage[]): number =>
  Math.max(
    0,
    messages.findLastIndex((_message, index) => startsSegment(messages, index)),
  );

const toContractMessage = (message: ExplanationUIMessage): ExplanationMessage => ({
  role: message.role === 'user' ? 'user' : 'assistant',
  content: textOf(message),
});

/**
 * Le LLM ne voit que le segment courant, et la sélection de sa dernière question : un
 * repère garde son sens à l'intérieur d'un segment. Une réponse vide n'est pas envoyée.
 */
export const toExplanationRequest = (
  messages: readonly ExplanationUIMessage[],
): ExplanationRequest => {
  const segment = messages.slice(currentSegmentStart(messages));
  return {
    selection: sourcesAt(messages, messages.length - 1).map((entry) => entry.identifier),
    messages: segment
      .filter((message) => message.role !== 'system')
      .map(toContractMessage)
      .filter((message) => message.content.length > 0),
  };
};
