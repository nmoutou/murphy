import { useChat } from '@ai-sdk/react';
import type { AppUIMessage } from '@murphy/contract/messages';
import { appMessageMetadataSchema } from '@murphy/contract/messages';
import { webSocketChatTransport } from '@/lib/webSocketChatTransport';
import { readErrorStage } from '@/lib/chatErrorStage';

export function useRagChat() {
  const { messages, sendMessage, stop, status, error, clearError, setMessages } =
    useChat<AppUIMessage>({
      transport: webSocketChatTransport,
      // Le transport vérifie les parts de données ; les métadonnées le sont ici
      messageMetadataSchema: appMessageMetadataSchema,
      onError: (chatError) => console.error('Chat request failed:', chatError),
      // Une réponse en échec ne laisse pas de bulle : la question reste, la modale dit pourquoi (ADR-041)
      onFinish: ({ isError, message }) => {
        if (!isError) return;
        setMessages((current) => current.filter((candidate) => candidate.id !== message.id));
      },
    });

  return {
    messages,
    sendMessage,
    stop,
    status,
    errorStage: error ? readErrorStage(error) : undefined,
    clearError,
  };
}
