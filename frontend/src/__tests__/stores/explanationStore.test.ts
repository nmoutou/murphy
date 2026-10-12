import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { textOf } from '@/lib/api/explanationRequest';
import { useErrorStore } from '@/stores/errorStore';
import {
  askQuestion,
  explanationChat,
  stopAnswer,
  summarize,
  SUMMARY_REQUEST,
} from '@/stores/explanationStore';
import type { SelectionEntry } from '@/stores/selectionStore';
import { useSelectionStore } from '@/stores/selectionStore';

const ENTRY: SelectionEntry = {
  identifier: 'LEGIARTI1',
  title: 'Article 2224',
  documentType: 'article',
  contentLength: 53,
};

const encoder = new TextEncoder();
const event = (chunk: object) => encoder.encode(`data: ${JSON.stringify(chunk)}\n\n`);
const START = [
  { type: 'start', messageId: 'a1' },
  { type: 'text-start', id: 'a1' },
];

/** Un flux SSE de l'AI SDK ; `isOpen` le laisse ouvert jusqu'à l'abandon de la requête */
const sseResponse = (
  chunks: object[],
  { isOpen = false, signal }: { isOpen?: boolean; signal?: AbortSignal } = {},
) =>
  new Response(
    new ReadableStream<Uint8Array>({
      start(controller) {
        chunks.forEach((chunk) => controller.enqueue(event(chunk)));
        if (!isOpen) {
          controller.enqueue(encoder.encode('data: [DONE]\n\n'));
          controller.close();
          return;
        }
        signal?.addEventListener('abort', () =>
          controller.error(new DOMException('aborted', 'AbortError')),
        );
      },
    }),
    { headers: { 'Content-Type': 'text/event-stream' } },
  );

const fetchMock = vi.fn<typeof fetch>();

const sentBody = () => JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body));
const roles = () => explanationChat.messages.map((message) => message.role);

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  explanationChat.messages = [];
  useSelectionStore.setState({ entries: [ENTRY] });
  useErrorStore.setState(useErrorStore.getInitialState(), true);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('explanationStore', () => {
  it('sends the summary request with the selection, and keeps the streamed answer', async () => {
    fetchMock.mockResolvedValue(
      sseResponse([
        ...START,
        { type: 'text-delta', id: 'a1', delta: 'Selon [1]' },
        { type: 'text-end', id: 'a1' },
        { type: 'finish' },
      ]),
    );

    await summarize();

    expect(sentBody()).toEqual({
      selection: ['LEGIARTI1'],
      messages: [{ role: 'user', content: SUMMARY_REQUEST }],
    });
    expect(String(fetchMock.mock.calls[0]?.[0])).toMatch(/\/api\/v1\/explanations$/);
    expect(explanationChat.messages[0]?.metadata).toEqual({ sources: [ENTRY] });
    expect(explanationChat.messages.map(textOf)).toEqual([SUMMARY_REQUEST, 'Selon [1]']);
  });

  it('keeps an answer stopped by the user, marked as interrupted', async () => {
    fetchMock.mockImplementation(async (_url, init) =>
      sseResponse([...START, { type: 'text-delta', id: 'a1', delta: 'Début' }], {
        isOpen: true,
        signal: init?.signal ?? undefined,
      }),
    );

    const pending = askQuestion('Que dit-il ?');
    await vi.waitFor(() => expect(explanationChat.messages).toHaveLength(2));
    await stopAnswer();
    await pending;

    expect(explanationChat.messages.map(textOf)).toEqual(['Que dit-il ?', 'Début']);
    expect(explanationChat.messages[1]?.metadata?.isInterrupted).toBe(true);
  });

  it('drops a partial answer on a stream error, keeps the question, and shows the code', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    fetchMock.mockResolvedValue(
      sseResponse([
        ...START,
        { type: 'text-delta', id: 'a1', delta: 'Début' },
        { type: 'error', errorText: 'LLM_FAILED' },
      ]),
    );

    await askQuestion('Que dit-il ?');

    expect(roles()).toEqual(['user']);
    expect(useErrorStore.getState().errorCode).toBe('LLM_FAILED');
  });

  it('shows the code of a refusal before the stream, the question kept', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    fetchMock.mockResolvedValue(
      Response.json({ status: { code: 400, message: 'CONTEXT_TOO_LARGE' } }, { status: 400 }),
    );

    await askQuestion('Que dit-il ?');

    expect(roles()).toEqual(['user']);
    expect(useErrorStore.getState().errorCode).toBe('CONTEXT_TOO_LARGE');
  });

  it('shows NETWORK when the backend does not answer', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));

    await askQuestion('Que dit-il ?');

    expect(useErrorStore.getState().errorCode).toBe('NETWORK');
  });
});
