import type { AppUIMessage, DocumentSource } from '@/types/messages';

export interface UserMessageProps {
  message: AppUIMessage;
}

export interface AIMessageProps {
  message: AppUIMessage;
  onCopy?: (content: string) => void;
  onSourceClick?: (source: DocumentSource) => void;
}
