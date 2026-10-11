import { create } from 'zustand';
import type { DisplayedErrorCode } from '@/lib/api/apiError';

interface ErrorState {
  /** Affiché par la modale tant qu'il est défini */
  readonly errorCode?: DisplayedErrorCode;
  readonly showError: (code: DisplayedErrorCode) => void;
  readonly clearError: () => void;
}

export const useErrorStore = create<ErrorState>()((set) => ({
  errorCode: undefined,
  showError: (errorCode) => set({ errorCode }),
  clearError: () => set({ errorCode: undefined }),
}));
