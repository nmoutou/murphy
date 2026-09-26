import type { ChatTransport, UIMessageChunk } from 'ai';
import type { AppUIMessage } from '@murphy/contract/messages';
import { getChatSocketUrl } from '@/lib/chatSocketUrl';
import { CONNECTION_ERROR_MESSAGE } from '@/lib/chatErrorStage';

type SendMessagesOptions = Parameters<ChatTransport<AppUIMessage>['sendMessages']>[0];

interface StreamState {
  /** Set once the stream is closed, errored or cancelled: nothing more is written to it */
  isSettled: boolean;
}

interface SocketBinding {
  readonly socket: WebSocket;
  readonly controller: ReadableStreamDefaultController<UIMessageChunk>;
  readonly state: StreamState;
  readonly options: SendMessagesOptions;
}

/** The backend closes the socket after these parts: any other close drops the answer */
const FINAL_CHUNK_TYPES: ReadonlySet<string> = new Set(['finish', 'error']);

const isMessageChunk = (value: unknown): value is UIMessageChunk =>
  typeof value === 'object' && value !== null && 'type' in value && typeof value.type === 'string';

/** The socket is a system boundary: a part must at least carry its type */
const parseChunk = (data: unknown): UIMessageChunk => {
  const value: unknown = typeof data === 'string' ? JSON.parse(data) : undefined;
  if (!isMessageChunk(value)) throw new Error('The chat socket sent a part without a type');
  return value;
};

/**
 * Pipes the socket into the stream `useChat` reads. The stream settles once: closed after
 * the final part or an abort, errored when the socket fails or drops before the end.
 */
const bindSocket = ({ socket, controller, state, options }: SocketBinding): void => {
  let hasFinalChunk = false;
  const settle = (error?: Error) => {
    if (state.isSettled) return;
    state.isSettled = true;
    if (error) controller.error(error);
    else controller.close();
  };
  const handleMessage = (event: MessageEvent) => {
    if (state.isSettled) return;
    try {
      const chunk = parseChunk(event.data);
      hasFinalChunk = FINAL_CHUNK_TYPES.has(chunk.type);
      controller.enqueue(chunk);
    } catch (error) {
      settle(error instanceof Error ? error : new Error(String(error)));
    }
    if (hasFinalChunk || state.isSettled) socket.close();
  };

  socket.onopen = () => socket.send(JSON.stringify({ messages: options.messages }));
  socket.onmessage = handleMessage;
  socket.onerror = () => settle(new Error(CONNECTION_ERROR_MESSAGE));
  socket.onclose = () => settle(hasFinalChunk ? undefined : new Error(CONNECTION_ERROR_MESSAGE));
  const handleAbort = () => {
    settle();
    socket.close();
  };
  options.abortSignal?.addEventListener('abort', handleAbort, { once: true });
};

/** One WebSocket per question: the backend streams the answer, then closes it */
export const webSocketChatTransport: ChatTransport<AppUIMessage> = {
  sendMessages: async (options) => {
    const socket = new WebSocket(getChatSocketUrl());
    const state: StreamState = { isSettled: false };
    return new ReadableStream<UIMessageChunk>({
      start: (controller) => bindSocket({ socket, controller, state, options }),
      // useChat stopped reading (abort, or an invalid part): closing the socket stops the backend
      cancel: () => {
        state.isSettled = true;
        socket.close();
      },
    });
  },
  reconnectToStream: async () => null,
};
