import { create } from 'zustand';
import type { StoreApi } from 'zustand';
import type { SearchRequest, SearchResponse } from '@murphy/contract/search';
import { reportApiError } from '@/lib/api/apiError';
import { searchDocuments } from '@/lib/api/search';
import { useErrorStore } from './errorStore';

const FIRST_PAGE = 1;

export type SearchStatus = 'idle' | 'loading' | 'success' | 'error';

interface SearchState {
  readonly question: string;
  readonly page: number;
  /** Absente avant la première réponse : le serveur applique sa taille par défaut */
  readonly pageSize?: number;
  readonly status: SearchStatus;
  readonly response?: SearchResponse;
  /** Celui de la dernière réponse, gardé après une erreur : la sélection survit à une recherche */
  readonly contextBudget?: number;
  /** Ne rejettent jamais : une erreur passe par la modale */
  readonly submit: (question: string) => Promise<void>;
  readonly goToPage: (page: number) => Promise<void>;
  readonly setPageSize: (pageSize: number) => Promise<void>;
}

type SetSearchState = StoreApi<SearchState>['setState'];

/** Une requête chasse la précédente : une réponse en retard n'écrase jamais la plus récente */
let pendingSearch: AbortController | undefined;

const runSearch = async (set: SetSearchState, request: SearchRequest): Promise<void> => {
  pendingSearch?.abort();
  const controller = new AbortController();
  pendingSearch = controller;
  const { question, page, pageSize } = request;
  set({ question, page, pageSize, status: 'loading' });
  try {
    const response = await searchDocuments(request, controller.signal);
    if (controller.signal.aborted) return;
    const { pageSize, contextBudget } = response;
    set({ status: 'success', response, pageSize, contextBudget });
  } catch (error) {
    if (controller.signal.aborted) return;
    set({ status: 'error', response: undefined });
    useErrorStore.getState().showError(reportApiError(error));
  }
};

export const useSearchStore = create<SearchState>()((set, get) => ({
  question: '',
  page: FIRST_PAGE,
  pageSize: undefined,
  status: 'idle',
  response: undefined,
  contextBudget: undefined,
  submit: (question) => runSearch(set, { question, page: FIRST_PAGE, pageSize: get().pageSize }),
  goToPage: (page) => runSearch(set, { question: get().question, page, pageSize: get().pageSize }),
  setPageSize: (pageSize) =>
    runSearch(set, { question: get().question, page: FIRST_PAGE, pageSize }),
}));
