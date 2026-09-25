/**
 * Chat Service Tests
 * The RAG pipeline end to end, with its infrastructure boundaries mocked
 */

import type { InferUIMessageChunk } from 'ai';
import { createChatStream, extractQuestionFromMessages } from '../../services/chatService';
import { embeddingClient, llmProvider, qdrantClient } from '../../infra';
import { fetchDocuments } from '../../infra/mongodb';
import { RagError } from '../../types/rag';
import type { AppUIMessage } from '../../types/messages';

jest.mock('../../infra', () => ({
  embeddingClient: { embedText: jest.fn() },
  qdrantClient: { searchVectors: jest.fn() },
  llmProvider: { stream: jest.fn() },
}));
jest.mock('../../infra/mongodb', () => ({ fetchDocuments: jest.fn() }));
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

type AppChunk = InferUIMessageChunk<AppUIMessage>;

const EMBEDDING = [0.1, 0.2, 0.3];
const QUESTION = 'Quel est le délai de prescription ?';

const userMessage = (text: string, id = 'user-1'): AppUIMessage => ({
  id,
  role: 'user',
  parts: [{ type: 'text', text }],
});

const readAllParts = async (stream: ReadableStream<AppChunk>): Promise<AppChunk[]> => {
  const parts: AppChunk[] = [];
  for await (const part of stream) parts.push(part);
  return parts;
};

const mockLlmTokens = (...tokens: string[]): void => {
  jest.mocked(llmProvider.stream).mockImplementation(async function* () {
    yield* tokens;
  });
};

beforeEach(() => {
  jest.mocked(embeddingClient.embedText).mockResolvedValue(EMBEDDING);
  jest.mocked(qdrantClient.searchVectors).mockResolvedValue([
    { id: '1', similarity: 0.91, payload: { chunkId: 'chunk-1', title: 'Code civil, art. 2224', type: 'LEGI' } },
    { id: '2', similarity: 0.72, payload: {} },
  ]);
  jest.mocked(fetchDocuments).mockResolvedValue([
    { chunkId: 'chunk-1', title: 'Code civil, art. 2224', content: 'Les actions personnelles se prescrivent par cinq ans.' },
  ]);
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
        { type: 'data-document', data: { chunkId: 'chunk-1', score: 1 } },
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
    await expect(createChatStream([userMessage('   ')])).rejects.toThrow('No question provided');
    expect(embeddingClient.embedText).not.toHaveBeenCalled();
  });

  it('streams sources, then the answer, then the timing metadata', async () => {
    const parts = await readAllParts(await createChatStream([userMessage(QUESTION)]));

    expect(parts.map((part) => part.type)).toEqual([
      'start', 'text-start', 'data-document', 'text-delta', 'text-delta', 'text-end', 'finish',
    ]);
    expect(parts[2]).toMatchObject({
      type: 'data-document',
      data: { chunkId: 'chunk-1', title: 'Code civil, art. 2224', type: 'LEGI', score: 0.91 },
    });
    expect(parts.filter((part) => part.type === 'text-delta').map((part) => part.delta)).toEqual(['Cinq ', 'ans.']);

    const finish = parts[parts.length - 1];
    expect(finish.type === 'finish' && Object.keys(finish.messageMetadata?.ragTiming ?? {}).sort()).toEqual(
      ['docFetchMs', 'embeddingMs', 'llmMs', 'retrievalMs', 'totalMs'],
    );
  });

  it('feeds the retrieved content to the LLM, never the chunks without id', async () => {
    await readAllParts(await createChatStream([userMessage(QUESTION)]));

    expect(qdrantClient.searchVectors).toHaveBeenCalledWith(EMBEDDING, 5);
    expect(fetchDocuments).toHaveBeenCalledWith(['chunk-1']);

    const [llmMessages] = jest.mocked(llmProvider.stream).mock.calls[0];
    expect(llmMessages[0].role).toBe('system');
    expect(llmMessages[0].content).toContain('[1] Code civil, art. 2224\nLes actions personnelles se prescrivent par cinq ans.');
    expect(llmMessages[1]).toEqual({ role: 'user', content: QUESTION });
  });

  it('ends with an error part when the LLM fails mid-stream', async () => {
    jest.mocked(llmProvider.stream).mockImplementation(async function* () {
      yield 'Cinq ';
      throw new RagError('llm', 'API_ERROR', 'Failed to stream LLM response: 502');
    });

    const parts = await readAllParts(await createChatStream([userMessage(QUESTION)]));

    expect(parts[parts.length - 1]).toEqual({ type: 'error', errorText: 'Failed to stream LLM response: 502' });
    expect(parts.some((part) => part.type === 'finish')).toBe(false);
  });

  it('ends with an error part when a stage before the LLM fails', async () => {
    jest.mocked(embeddingClient.embedText).mockRejectedValue(
      new RagError('embedding', 'NETWORK', 'Failed to generate embeddings: ECONNREFUSED'),
    );

    const parts = await readAllParts(await createChatStream([userMessage(QUESTION)]));

    expect(parts[parts.length - 1]).toEqual({ type: 'error', errorText: 'Failed to generate embeddings: ECONNREFUSED' });
    expect(llmProvider.stream).not.toHaveBeenCalled();
  });
});
