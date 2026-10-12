import type { SelectionEntry } from '@/stores/selectionStore';

/** Indicatif : le serveur compte aussi les métadonnées, le prompt et la conversation */
export const sumContentLength = (entries: readonly SelectionEntry[]): number =>
  entries.reduce((total, entry) => total + entry.contentLength, 0);

export const isOverBudget = (entries: readonly SelectionEntry[], budget: number): boolean =>
  sumContentLength(entries) > budget;

/** Sans document, rien à expliquer ; sans budget, aucune recherche n'a encore répondu */
export const canExplain = (entries: readonly SelectionEntry[], budget?: number): boolean =>
  entries.length > 0 && budget !== undefined && !isOverBudget(entries, budget);
