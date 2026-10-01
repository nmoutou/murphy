import type { ChatTransport, UIMessageChunk } from 'ai';
import type { AppUIMessage } from '@murphy/contract/messages';
import { appDataPartSchemas } from '@murphy/contract/messages';
import { getChatSocketUrl } from '@/lib/chatSocketUrl';
import { CONNECTION_ERROR_MESSAGE } from '@/lib/chatErrorStage';

type SendMessagesOptions = Parameters<ChatTransport<AppUIMessage>['sendMessages']>[0];

interface StreamState {
  /** Vrai une fois le flux fermé, en erreur ou annulé : plus rien n'y est écrit */
  isSettled: boolean;
}

interface SocketBinding {
  readonly socket: WebSocket;
  readonly controller: ReadableStreamDefaultController<UIMessageChunk>;
  readonly state: StreamState;
  readonly options: SendMessagesOptions;
}

/** Le backend ferme après ces parts : toute autre fermeture abandonne la réponse */
const FINAL_CHUNK_TYPES: ReadonlySet<string> = new Set(['finish', 'error']);
const DATA_PART_PREFIX = 'data-';

type DataPartName = keyof typeof appDataPartSchemas;

const isMessageChunk = (value: unknown): value is UIMessageChunk =>
  typeof value === 'object' && value !== null && 'type' in value && typeof value.type === 'string';

const isDataPartName = (name: string): name is DataPartName =>
  Object.hasOwn(appDataPartSchemas, name);

/**
 * `useChat` cherche ses `dataPartSchemas` par type (`data-document`), or ils sont rangés
 * par nom (`document`) : ai 6.0.x ne les applique jamais, d'où la vérification ici
 */
const breaksDataContract = (chunk: UIMessageChunk): boolean => {
  if (!chunk.type.startsWith(DATA_PART_PREFIX)) return false;
  const name = chunk.type.slice(DATA_PART_PREFIX.length);
  if (!isDataPartName(name) || !('data' in chunk)) return true;
  return !appDataPartSchemas[name].safeParse(chunk.data).success;
};

/** La socket est une frontière : une part porte son type, une part de données son contrat */
const parseChunk = (data: unknown): UIMessageChunk => {
  const value: unknown = typeof data === 'string' ? JSON.parse(data) : undefined;
  if (!isMessageChunk(value)) throw new Error('The chat socket sent a part without a type');
  if (breaksDataContract(value)) {
    throw new Error(`The chat socket sent a ${value.type} part that breaks the contract`);
  }
  return value;
};

/**
 * Le backend ne lit que la dernière question : les réponses passées, qui portent des
 * documents entiers, feraient dépasser la taille limite de la requête
 */
const selectQuestion = (messages: readonly AppUIMessage[]): AppUIMessage[] => {
  const question = messages.findLast((message) => message.role === 'user');
  return question ? [question] : [];
};

/**
 * Le flux se termine une seule fois : fermé après la part finale ou un abandon, en erreur
 * si la socket échoue ou tombe avant la fin.
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

  socket.onopen = () => socket.send(JSON.stringify({ messages: selectQuestion(options.messages) }));
  socket.onmessage = handleMessage;
  socket.onerror = () => settle(new Error(CONNECTION_ERROR_MESSAGE));
  socket.onclose = () => settle(hasFinalChunk ? undefined : new Error(CONNECTION_ERROR_MESSAGE));
  const handleAbort = () => {
    settle();
    socket.close();
  };
  options.abortSignal?.addEventListener('abort', handleAbort, { once: true });
};

/** Une WebSocket par question : le backend envoie la réponse puis la ferme */
export const webSocketChatTransport: ChatTransport<AppUIMessage> = {
  sendMessages: async (options) => {
    const socket = new WebSocket(getChatSocketUrl());
    const state: StreamState = { isSettled: false };
    return new ReadableStream<UIMessageChunk>({
      start: (controller) => bindSocket({ socket, controller, state, options }),
      // useChat a cessé de lire (abandon ou part invalide) : fermer la socket arrête le backend
      cancel: () => {
        state.isSettled = true;
        socket.close();
      },
    });
  },
  reconnectToStream: async () => null,
};
