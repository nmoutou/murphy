/**
 * Chat Service Tests
 * The RAG pipeline end to end, with its infrastructure boundaries mocked
 */

import type { InferUIMessageChunk } from 'ai';
import { createChatStream, extractQuestionFromMessages } from '../../services/chatService';
import { getInfraClients } from '../../infra/clients';
import { RagError } from '../../types/rag';
import type { AppUIMessage } from '@murphy/contract/messages';
import { serializeChatError } from '@murphy/contract/errors';
import type { RetrievedChunk, StoredDocument } from '../../types/rag';

jest.mock('../../infra/clients', () => {
  const clients = {
    embedding: { embedText: jest.fn() },
    qdrant: { searchVectors: jest.fn() },
    mongo: { fetchParentDocuments: jest.fn() },
    llm: { stream: jest.fn() },
  };
  return { getInfraClients: () => clients };
});
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

type AppChunk = InferUIMessageChunk<AppUIMessage>;

const { embedding, qdrant, mongo, llm } = getInfraClients();

const EMBEDDING = [0.1, 0.2, 0.3];
const QUESTION = 'Quel est le délai de prescription ?';
const FIRST_SENTENCE = 'Les actions personnelles se prescrivent par cinq ans.';
const SECOND_SENTENCE = 'Le délai court du jour de la connaissance des faits.';
const DOCUMENT: StoredDocument = {
  identifier: 'LEGIARTI000006419304',
  ownerId: 'default',
  title: 'Code civil, art. 2224',
  content: `${FIRST_SENTENCE} ${SECOND_SENTENCE}`,
};
const chunkOf = (chunkId: string, charStart: number, text: string, score: number): RetrievedChunk => ({
  chunkId,
  identifier: DOCUMENT.identifier,
  ownerId: DOCUMENT.ownerId,
  charStart,
  charEnd: charStart + text.length,
  score,
  type: 'article',
});
const SECOND_START = FIRST_SENTENCE.length + 1;
/** Two passages of the same article, the second ranked first */
const CHUNKS = [chunkOf('chunk-2', SECOND_START, SECOND_SENTENCE, 0.91), chunkOf('chunk-1', 0, FIRST_SENTENCE, 0.72)];

const userMessage = (text: string, id = 'user-1'): AppUIMessage => ({
  id,
  role: 'user',
  parts: [{ type: 'text', text }],
});

/** A client that stays until the end */
const NOT_ABORTED = new AbortController().signal;

const readAllParts = async (stream: ReadableStream<AppChunk>): Promise<AppChunk[]> => {
  const parts: AppChunk[] = [];
  for await (const part of stream) parts.push(part);
  return parts;
};

const mockLlmTokens = (...tokens: string[]): void => {
  jest.mocked(llm.stream).mockImplementation(async function* () {
    yield* tokens;
  });
};

beforeEach(() => {
  jest.mocked(embedding.embedText).mockResolvedValue(EMBEDDING);
  jest.mocked(qdrant.searchVectors).mockResolvedValue(CHUNKS);
  jest.mocked(mongo.fetchParentDocuments).mockResolvedValue([DOCUMENT]);
  mockLlmTokens('Cinq ', 'ans.');
});

describe('extractQuestionFromMessages', () => {
  it('reads the last user message only', () => {
    const messages: AppUIMessage[] = [
      userMessage('première question', 'user-1'),
      { id: 'assistant-1', role: 'assistant', parts: [{ type: 'text', text: 'réponse' }] },
      userMessage('seconde question', 'user-2'),
    ];

    expect(extractQuestionFromMessages(messages)).toBe('seconde question');
  });

  it('joins the text parts and ignores the other parts', () => {
    const message: AppUIMessage = {
      id: 'user-1',
      role: 'user',
      parts: [
        { type: 'text', text: 'Quel délai ' },
        { type: 'data-document', data: { chunkId: 'chunk-1', identifier: 'LEGIARTI1', highlightStart: 0, highlightEnd: 4, score: 1 } },
        { type: 'text', text: 'pour agir ?' },
      ],
    };

    expect(extractQuestionFromMessages([message])).toBe('Quel délai pour agir ?');
  });

  it('returns an empty string without any user message', () => {
    const messages: AppUIMessage[] = [{ id: 'system-1', role: 'system', parts: [{ type: 'text', text: 'consigne' }] }];

    expect(extractQuestionFromMessages(messages)).toBe('');
  });
});

describe('createChatStream', () => {
  it('rejects a blank question before running the pipeline', async () => {
    await expect(createChatStream([userMessage('   ')], NOT_ABORTED)).rejects.toMatchObject({
      stage: 'request',
      code: 'NO_QUESTION',
    });
    expect(embedding.embedText).not.toHaveBeenCalled();
  });

  it('streams the parent document once, then its passages, then the answer and the timing', async () => {
    const parts = await readAllParts(await createChatStream([userMessage(QUESTION)], NOT_ABORTED));

    expect(parts.map((part) => part.type)).toEqual([
      'start', 'text-start', 'data-parentDocument', 'data-document', 'data-document',
      'text-delta', 'text-delta', 'text-end', 'finish',
    ]);
    expect(parts[2]).toEqual({
      type: 'data-parentDocument',
      data: { identifier: DOCUMENT.identifier, title: DOCUMENT.title, type: 'article', content: DOCUMENT.content },
    });
    expect(parts[3]).toEqual({
      type: 'data-document',
      data: {
        chunkId: 'chunk-2',
        identifier: DOCUMENT.identifier,
        highlightStart: SECOND_START,
        highlightEnd: DOCUMENT.content.length,
        score: 0.91,
        title: DOCUMENT.title,
        type: 'article',
      },
    });
    expect(parts[4]).toMatchObject({ type: 'data-document', data: { chunkId: 'chunk-1', highlightStart: 0 } });
    expect(parts.filter((part) => part.type === 'text-delta').map((part) => part.delta)).toEqual(['Cinq ', 'ans.']);

    const finish = parts[parts.length - 1];
    expect(finish.type === 'finish' && Object.keys(finish.messageMetadata?.ragTiming ?? {}).sort()).toEqual(
      ['docFetchMs', 'embeddingMs', 'llmMs', 'retrievalMs', 'totalMs'],
    );
  });

  it('feeds each passage to the LLM, not the whole document', async () => {
    await readAllParts(await createChatStream([userMessage(QUESTION)], NOT_ABORTED));

    expect(qdrant.searchVectors).toHaveBeenCalledWith(EMBEDDING, 5);
    expect(mongo.fetchParentDocuments).toHaveBeenCalledWith(CHUNKS);

    const [llmMessages] = jest.mocked(llm.stream).mock.calls[0];
    expect(llmMessages[0].role).toBe('system');
    expect(llmMessages[0].content).toContain(
      `[1] Code civil, art. 2224\n${SECOND_SENTENCE}\n\n[2] Code civil, art. 2224\n${FIRST_SENTENCE}`,
    );
    expect(llmMessages[0].content).not.toContain(DOCUMENT.content);
    expect(llmMessages[1]).toEqual({ role: 'user', content: QUESTION });
  });

  it('ends with the stage and code, before any source, when the databases break the contract', async () => {
    jest.mocked(mongo.fetchParentDocuments).mockResolvedValue([]);

    const parts = await readAllParts(await createChatStream([userMessage(QUESTION)], NOT_ABORTED));

    expect(parts.map((part) => part.type)).toEqual(['start', 'text-start', 'error']);
    expect(parts[2]).toEqual({
      type: 'error',
      errorText: serializeChatError({ stage: 'retrieval', code: 'CONTRACT_VIOLATION' }),
    });
    expect(llm.stream).not.toHaveBeenCalled();
  });

  it('ends with an error part when the LLM fails mid-stream', async () => {
    jest.mocked(llm.stream).mockImplementation(async function* () {
      yield 'Cinq ';
      throw new RagError('llm', 'API_ERROR', 'Failed to stream LLM response: 502');
    });

    const parts = await readAllParts(await createChatStream([userMessage(QUESTION)], NOT_ABORTED));

    expect(parts[parts.length - 1]).toEqual({
      type: 'error',
      errorText: serializeChatError({ stage: 'llm', code: 'API_ERROR' }),
    });
    expect(parts.some((part) => part.type === 'finish')).toBe(false);
  });

  it('ends with an error part when a stage before the LLM fails', async () => {
    jest.mocked(embedding.embedText).mockRejectedValue(
      new RagError('embedding', 'NETWORK', 'Failed to generate embeddings: ECONNREFUSED'),
    );

    const parts = await readAllParts(await createChatStream([userMessage(QUESTION)], NOT_ABORTED));

    expect(parts[parts.length - 1]).toEqual({
      type: 'error',
      errorText: serializeChatError({ stage: 'embedding', code: 'NETWORK' }),
    });
    expect(llm.stream).not.toHaveBeenCalled();
  });

  it('tells nothing of an unexpected failure but that it is internal', async () => {
    jest.mocked(embedding.embedText).mockRejectedValue(new Error('connect ECONNREFUSED 10.0.0.3:80'));

    const parts = await readAllParts(await createChatStream([userMessage(QUESTION)], NOT_ABORTED));

    expect(parts[parts.length - 1]).toEqual({
      type: 'error',
      errorText: serializeChatError({ stage: 'internal', code: 'INTERNAL' }),
    });
  });
});

describe('createChatStream, once the client has left', () => {
  it('hands its abort signal to the LLM', async () => {
    const abortController = new AbortController();

    await readAllParts(await createChatStream([userMessage(QUESTION)], abortController.signal));

    expect(llm.stream).toHaveBeenCalledWith(expect.any(Array), abortController.signal);
  });

  it('does not call the LLM when the client left during the retrieval', async () => {
    const abortController = new AbortController();
    abortController.abort();

    const parts = await readAllParts(await createChatStream([userMessage(QUESTION)], abortController.signal));

    expect(llm.stream).not.toHaveBeenCalled();
    expect(parts.some((part) => part.type === 'error' || part.type === 'finish')).toBe(false);
  });

  it('ends without an error or a finish part when the client leaves during the answer', async () => {
    const abortController = new AbortController();
    jest.mocked(llm.stream).mockImplementation(async function* () {
      yield 'Cinq ';
      abortController.abort();
    });

    const parts = await readAllParts(await createChatStream([userMessage(QUESTION)], abortController.signal));

    expect(parts.map((part) => part.type).slice(-1)).toEqual(['text-delta']);
  });
});
