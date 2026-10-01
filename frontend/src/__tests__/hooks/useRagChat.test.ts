// Le faux backend envoie les parts de `backend/src/services/chatService.ts`, dans son ordre

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import type { UIMessageChunk } from 'ai';
import { serializeChatError } from '@murphy/contract/errors';
import { useRagChat } from '@/hooks/useRagChat';
import { getMessageText } from '@/lib/messageText';
import { stubWebSocket } from '../fakeWebSocket';
import type { FakeWebSocket } from '../fakeWebSocket';

const QUESTION = 'Quel délai de prescription ?';
const ANSWER_ID = 'answer-1';
const PARENT = {
  identifier: 'LEGIARTI000006419280',
  title: 'Article 2224',
  documentType: 'article' as const,
  content: 'Les actions…',
};
const PASSAGE = {
  chunkId: 'c-1',
  identifier: PARENT.identifier,
  highlightStart: 0,
  highlightEnd: 12,
  score: 0.8,
  documentType: 'article' as const,
};
const RAG_TIMING = { embeddingMs: 4, retrievalMs: 6, totalMs: 900 };

const ANSWER_START: UIMessageChunk[] = [
  { type: 'start', messageId: ANSWER_ID },
  { type: 'text-start', id: ANSWER_ID },
];
const SOURCES: UIMessageChunk[] = [
  { type: 'data-parentDocument', data: PARENT },
  { type: 'data-document', data: PASSAGE },
];
const ANSWER_END: UIMessageChunk[] = [
  { type: 'text-delta', id: ANSWER_ID, delta: 'Cinq ans.' },
  { type: 'text-end', id: ANSWER_ID },
];
const FINISH: UIMessageChunk = {
  type: 'finish',
  finishReason: 'stop',
  messageMetadata: { ragTiming: RAG_TIMING },
};

const SETTLED_STATUSES = ['ready', 'error'];

const receiveAll = (socket: FakeWebSocket, parts: UIMessageChunk[]) =>
  parts.forEach((part) => socket.receive(part));

/** Le hook, et de quoi poser la question : résolu une fois la socket ouverte */
const renderChat = () => {
  const sockets = stubWebSocket();
  const { result } = renderHook(() => useRagChat());

  const ask = async () => {
    let sending: Promise<void> = Promise.resolve();
    act(() => {
      sending = result.current.sendMessage({ text: QUESTION });
    });
    await waitFor(() => expect(sockets).toHaveLength(1));
    const [socket] = sockets;
    act(() => socket.open());
    return { socket, sending };
  };

  /**
   * Le côté backend, jusqu'à ce que useChat en ait fini. Une réponse qui ne se termine
   * jamais fait échouer `waitFor` au lieu de laisser un `act` ouvert pour la suite.
   */
  const answer = async (reply: () => void, sending: Promise<void>) => {
    act(reply);
    await waitFor(() => expect(SETTLED_STATUSES).toContain(result.current.status));
    await act(() => sending);
  };

  return { result, ask, answer };
};

describe('useRagChat', () => {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
  });

  it('sends the question and shows the answer with its sources and timing', async () => {
    const { result, ask, answer } = renderChat();

    const { socket, sending } = await ask();
    await answer(
      () => receiveAll(socket, [...ANSWER_START, ...SOURCES, ...ANSWER_END, FINISH]),
      sending,
    );

    const [sentQuestion] = JSON.parse(socket.sent[0]).messages;
    expect(getMessageText(sentQuestion)).toBe(QUESTION);
    const [question, reply] = result.current.messages;
    expect(getMessageText(question)).toBe(QUESTION);
    expect(getMessageText(reply)).toBe('Cinq ans.');
    expect(reply.parts).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ type: 'data-parentDocument', data: PARENT }),
        expect.objectContaining({ type: 'data-document', data: PASSAGE }),
      ]),
    );
    expect(reply.metadata).toEqual({ ragTiming: RAG_TIMING });
    expect(result.current.status).toBe('ready');
    expect(result.current.errorStage).toBeUndefined();
  });

  it.each<[string, UIMessageChunk[]]>([
    [
      'a passage whose score is not a number',
      [{ type: 'data-document', data: { ...PASSAGE, score: 'haut' } }],
    ],
    [
      'malformed timing metadata',
      [...ANSWER_END, { type: 'finish', messageMetadata: { ragTiming: { totalMs: 'lent' } } }],
    ],
  ])(
    'rejects %s: internal error, the answer is removed, the question stays',
    async (_case, invalidParts) => {
      const { result, ask, answer } = renderChat();

      const { socket, sending } = await ask();
      await answer(() => receiveAll(socket, [...ANSWER_START, ...invalidParts]), sending);

      expect(result.current.errorStage).toBe('internal');
      expect(result.current.messages.map(getMessageText)).toEqual([QUESTION]);
      expect(console.error).toHaveBeenCalledWith('Chat request failed:', expect.any(Error));
    },
  );

  it('names the stage the backend reports, and removes the failed answer', async () => {
    const { result, ask, answer } = renderChat();
    const errorPart: UIMessageChunk = {
      type: 'error',
      errorText: serializeChatError({ stage: 'retrieval', code: 'TIMEOUT' }),
    };

    const { socket, sending } = await ask();
    await answer(() => receiveAll(socket, [...ANSWER_START, errorPart]), sending);

    expect(result.current.errorStage).toBe('retrieval');
    expect(result.current.messages.map(getMessageText)).toEqual([QUESTION]);
  });

  it('names the connection when the socket drops before the end, until the error is cleared', async () => {
    const { result, ask, answer } = renderChat();

    const { socket, sending } = await ask();
    await answer(() => {
      receiveAll(socket, [...ANSWER_START, ...SOURCES]);
      socket.drop();
    }, sending);

    expect(result.current.errorStage).toBe('connection');
    expect(result.current.messages.map(getMessageText)).toEqual([QUESTION]);

    act(() => result.current.clearError());

    expect(result.current.errorStage).toBeUndefined();
  });

  it('stops a streaming answer: the socket closes and the chat is ready again', async () => {
    const { result, ask } = renderChat();

    const { socket, sending } = await ask();
    act(() => receiveAll(socket, [...ANSWER_START, ...SOURCES]));
    await waitFor(() => expect(result.current.status).toBe('streaming'));
    await act(() => result.current.stop());
    await waitFor(() => expect(result.current.status).toBe('ready'));
    await act(() => sending);

    expect(socket.close).toHaveBeenCalled();
    expect(result.current.status).toBe('ready');
    expect(result.current.errorStage).toBeUndefined();
  });
});
