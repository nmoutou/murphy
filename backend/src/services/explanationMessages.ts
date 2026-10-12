import type { LlmMessage } from '../infra/llm';

const MERGED_MESSAGE_SEPARATOR = '\n\n';

/**
 * Une question restée sans réponse (une erreur l'a effacée) part avec la suivante :
 * certains modèles refusent deux messages du même rôle à la suite.
 */
export const mergeConsecutiveUserMessages = (messages: readonly LlmMessage[]): LlmMessage[] =>
  messages.reduce<LlmMessage[]>((merged, message) => {
    const previous = merged[merged.length - 1];
    if (previous?.role !== 'user' || message.role !== 'user') return [...merged, message];
    const content = `${previous.content}${MERGED_MESSAGE_SEPARATOR}${message.content}`;
    return [...merged.slice(0, -1), { role: 'user', content }];
  }, []);

/** Comme `content_length` à l'ingestion : des points de code, pas des unités UTF-16 */
export const countCodePoints = (text: string): number => [...text].length;
