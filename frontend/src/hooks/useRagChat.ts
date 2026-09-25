import { useChat } from '@ai-sdk/react';
import type { ChatTransport } from 'ai';
import type { AppUIMessage } from '@murphy/contract/messages';
import { appDataPartSchemas, appMessageMetadataSchema } from '@murphy/contract/messages';

class WebSocketChatTransport implements ChatTransport<AppUIMessage> {
  private url: string;

  constructor(url: string) {
    this.url = url;
  }

  async sendMessages({ messages, abortSignal }: Parameters<ChatTransport<AppUIMessage>['sendMessages']>[0]) {
    return new Promise<ReadableStream<any>>((resolve, reject) => {
      const ws = new WebSocket(this.url);

      const stream = new ReadableStream({
        start(controller) {
          const abort = () => ws.close();

          if (abortSignal) {
            abortSignal.addEventListener('abort', abort);
          }

          ws.onopen = () => {
            ws.send(JSON.stringify({ messages }));
          };

          ws.onmessage = (event) => {
            try {
              const chunk = JSON.parse(event.data as string);
              controller.enqueue(chunk);
            } catch (error) {
              controller.error(error);
            }
          };

          ws.onerror = () => {
            controller.error(new Error('WebSocket error'));
            reject(new Error('WebSocket error'));
          };

          ws.onclose = () => {
            controller.close();
            if (abortSignal) {
              abortSignal.removeEventListener('abort', abort);
            }
          };
        },
        cancel() {
          ws.close();
        },
      });

      resolve(stream);
    });
  }

  async reconnectToStream() {
    return null;
  }
}

export function useRagChat() {
  const { messages, sendMessage, stop, status } = useChat<AppUIMessage>({
    transport: new WebSocketChatTransport(process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:5000/api/v1/chat/ws'),
    // The socket is an external boundary: a part that breaks the contract is rejected here
    dataPartSchemas: appDataPartSchemas,
    messageMetadataSchema: appMessageMetadataSchema,
  });

  return {
    messages,
    sendMessage,
    stop,
    status,
  };
}
