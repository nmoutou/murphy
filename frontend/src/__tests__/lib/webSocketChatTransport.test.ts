/**
 * WebSocket Chat Transport Tests
 * The stream `useChat` reads, fed by a fake backend socket: it settles once, closed after
 * the final part or an abort, errored when the socket fails or drops before the end
 */

import { beforeEach, describe, expect, it } from 'vitest';
import type { UIMessageChunk } from 'ai';
import type { AppUIMessage } from '@murphy/contract/messages';
import { webSocketChatTransport } from '@/lib/webSocketChatTransport';
import { CONNECTION_ERROR_MESSAGE } from '@/lib/chatErrorStage';
import { stubWebSocket } from '../fakeWebSocket';
import type { FakeWebSocket } from '../fakeWebSocket';

const ANSWER_ID = 'answer-1';
const QUESTION: AppUIMessage = {
  id: 'question-1',
  role: 'user',
  parts: [{ type: 'text', text: 'Quel délai de prescription ?' }],
};
const ANSWER_PARTS: UIMessageChunk[] = [
  { type: 'start', messageId: ANSWER_ID },
  { type: 'text-start', id: ANSWER_ID },
  { type: 'text-delta', id: ANSWER_ID, delta: 'Cinq ans.' },
  { type: 'text-end', id: ANSWER_ID },
];
const FINISH: UIMessageChunk = { type: 'finish' };

interface StreamOutcome {
  readonly parts: UIMessageChunk[];
  readonly error?: unknown;
}

/** Reads the stream to its end: the parts it delivered, and its error if it failed */
const readStream = async (stream: ReadableStream<UIMessageChunk>): Promise<StreamOutcome> => {
  const parts: UIMessageChunk[] = [];
  const reader = stream.getReader();
  try {
    for (let read = await reader.read(); !read.done; read = await reader.read()) {
      parts.push(read.value);
    }
    return { parts };
  } catch (error) {
    return { parts, error };
  }
};

describe('webSocketChatTransport', () => {
  let sockets: FakeWebSocket[];

  beforeEach(() => {
    sockets = stubWebSocket();
  });

  const askQuestion = async (abortSignal?: AbortSignal) => {
    const stream = await webSocketChatTransport.sendMessages({
      trigger: 'submit-message',
      chatId: 'chat-1',
      messageId: undefined,
      messages: [QUESTION],
      abortSignal,
    });
    return { stream, socket: sockets[0] };
  };

  it('opens the chat socket and sends the conversation once it is open', async () => {
    const { socket } = await askQuestion();
    expect(socket.url).toMatch(/\/api\/v1\/chat\/ws$/);
    expect(socket.sent).toEqual([]);

    socket.open();

    expect(socket.sent.map((data) => JSON.parse(data))).toEqual([{ messages: [QUESTION] }]);
  });

  it('delivers the parts in order, then closes the stream and the socket after finish', async () => {
    const { stream, socket } = await askQuestion();

    socket.open();
    [...ANSWER_PARTS, FINISH].forEach((part) => socket.receive(part));

    expect(await readStream(stream)).toEqual({ parts: [...ANSWER_PARTS, FINISH] });
    expect(socket.close).toHaveBeenCalled();
  });

  it('ends the stream cleanly after an error part, which useChat reads', async () => {
    const { stream, socket } = await askQuestion();
    const errorPart: UIMessageChunk = {
      type: 'error',
      errorText: '{"stage":"llm","code":"TIMEOUT"}',
    };

    socket.receive(errorPart);

    expect(await readStream(stream)).toEqual({ parts: [errorPart] });
    expect(socket.close).toHaveBeenCalled();
  });

  it.each([
    ['closes before the final part', (socket: FakeWebSocket) => socket.drop()],
    ['fails', (socket: FakeWebSocket) => socket.fail()],
  ])('errors the stream when the socket %s', async (_case, endSocket) => {
    const { stream, socket } = await askQuestion();

    ANSWER_PARTS.forEach((part) => socket.receive(part));
    endSocket(socket);

    const { error } = await readStream(stream);
    expect(error).toEqual(new Error(CONNECTION_ERROR_MESSAGE));
  });

  it.each([
    ['text that is not JSON', (socket: FakeWebSocket) => socket.receiveRaw('pas du JSON')],
    ['a part without type', (socket: FakeWebSocket) => socket.receive({ delta: 'Cinq ans.' })],
  ])('errors the stream and closes the socket on %s', async (_case, sendInvalid) => {
    const { stream, socket } = await askQuestion();

    sendInvalid(socket);

    const { error } = await readStream(stream);
    expect(error).toBeInstanceOf(Error);
    expect(socket.close).toHaveBeenCalled();
  });

  it('closes the stream and the socket on abort, and ignores what arrives next', async () => {
    const abort = new AbortController();
    const { stream, socket } = await askQuestion(abort.signal);
    const [startPart, ...laterParts] = ANSWER_PARTS;

    socket.receive(startPart);
    abort.abort();
    laterParts.forEach((part) => socket.receive(part));

    expect(await readStream(stream)).toEqual({ parts: [startPart] });
    expect(socket.close).toHaveBeenCalled();
  });

  it('closes the socket when useChat stops reading', async () => {
    const { stream, socket } = await askQuestion();

    await stream.cancel();
    ANSWER_PARTS.forEach((part) => socket.receive(part));

    expect(socket.close).toHaveBeenCalled();
  });

  it('never resumes an answer: the backend keeps no stream', async () => {
    expect(await webSocketChatTransport.reconnectToStream({ chatId: 'chat-1' })).toBeNull();
  });
});
