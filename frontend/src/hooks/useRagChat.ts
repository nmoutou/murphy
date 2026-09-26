import { useChat } from '@ai-sdk/react';
import type { AppUIMessage } from '@murphy/contract/messages';
import { appDataPartSchemas, appMessageMetadataSchema } from '@murphy/contract/messages';
import { webSocketChatTransport } from '@/lib/webSocketChatTransport';
import { readErrorStage } from '@/lib/chatErrorStage';

export function useRagChat() {
  const { messages, sendMessage, stop, status, error, clearError, setMessages } =
    useChat<AppUIMessage>({
      transport: webSocketChatTransport,
      // The socket is an external boundary: a part that breaks the contract is rejected here
      dataPartSchemas: appDataPartSchemas,
      messageMetadataSchema: appMessageMetadataSchema,
      onError: (chatError) => console.error('Chat request failed:', chatError),
      // A failed answer leaves no bubble behind: the question stays, the modal says why (ADR-041)
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
