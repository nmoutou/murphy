import type { InferUIMessageChunk } from 'ai';
import { createChatStream, extractQuestionFromMessages } from '../../services/chatService';
import { getInfraClients } from '../../infra/clients';
import { RagError } from '../../types/rag';
import type { AppUIMessage } from '@murphy/contract/messages';
import { serializeChatError } from '@murphy/contract/errors';
import type { PassageRef, SearchHit, StoredDocument } from '../../types/rag';

jest.mock('../../infra/clients', () => {
  const clients = {
    embedding: { embedText: jest.fn() },
    opensearch: { search: jest.fn() },
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

const { embedding, opensearch, mongo, llm } = getInfraClients();

const EMBEDDING = [0.1, 0.2, 0.3];
const QUESTION = 'Quel est le délai de prescription ?';
const FIRST_SENTENCE = 'Les actions personnelles se prescrivent par cinq ans.';
const SECOND_SENTENCE = 'Le délai court du jour de la connaissance des faits.';
const DOCUMENT: StoredDocument = {
  identifier: 'LEGIARTI000006419304',
  title: 'Code civil, art. 2224',
  content: `${FIRST_SENTENCE} ${SECOND_SENTENCE}`,
};
const SECTION: StoredDocument = { identifier: 'LEGISCTA000006114781', title: 'Chapitre III', content: '' };
const refOf = (chunkId: string, charStart: number, text: string): PassageRef => ({
  chunkId,
  charStart,
  charEnd: charStart + text.length,
});
const SECOND_START = FIRST_SENTENCE.length + 1;
const FIRST_REF = refOf('chunk-1', 0, FIRST_SENTENCE);
const SECOND_REF = refOf('chunk-2', SECOND_START, SECOND_SENTENCE);
/** Une section, sans passage, classée devant un article dont le second passage est classé premier */
const HITS: SearchHit[] = [
  { identifier: SECTION.identifier, documentType: 'section', lexicalPassages: [], vectorPassages: [] },
  {
    identifier: DOCUMENT.identifier,
    documentType: 'article',
    lexicalPassages: [SECOND_REF, FIRST_REF],
    vectorPassages: [],
  },
];

const userMessage = (text: string, id = 'user-1'): AppUIMessage => ({
  id,
  role: 'user',
  parts: [{ type: 'text', text }],
});

/** Un client qui reste jusqu'au bout */
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
  jest.mocked(opensearch.search).mockResolvedValue(HITS);
  jest.mocked(mongo.fetchParentDocuments).mockResolvedValue([DOCUMENT, SECTION]);
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
        { type: 'data-document', data: { chunkId: 'chunk-1', identifier: 'LEGIARTI1', highlightStart: 0, highlightEnd: 4, documentType: 'article' } },
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

  it('streams each document in ranking order, then its passages, then the answer and the timing', async () => {
    const parts = await readAllParts(await createChatStream([userMessage(QUESTION)], NOT_ABORTED));

    expect(parts.map((part) => part.type)).toEqual([
      'start', 'text-start', 'data-parentDocument', 'data-parentDocument', 'data-document', 'data-document',
      'text-delta', 'text-delta', 'text-end', 'finish',
    ]);
    expect(parts[2]).toMatchObject({ type: 'data-parentDocument', data: { identifier: SECTION.identifier, documentType: 'section' } });
    expect(parts[3]).toEqual({
      type: 'data-parentDocument',
      data: { identifier: DOCUMENT.identifier, title: DOCUMENT.title, documentType: 'article', content: DOCUMENT.content },
    });
    expect(parts[4]).toEqual({
      type: 'data-document',
      data: {
        chunkId: 'chunk-2',
        identifier: DOCUMENT.identifier,
        highlightStart: SECOND_START,
        highlightEnd: DOCUMENT.content.length,
        title: DOCUMENT.title,
        documentType: 'article',
      },
    });
    expect(parts[5]).toMatchObject({ type: 'data-document', data: { chunkId: 'chunk-1', highlightStart: 0 } });
    expect(parts.filter((part) => part.type === 'text-delta').map((part) => part.delta)).toEqual(['Cinq ', 'ans.']);

    const finish = parts[parts.length - 1];
    expect(finish.type === 'finish' && Object.keys(finish.messageMetadata?.ragTiming ?? {}).sort()).toEqual(
      ['docFetchMs', 'embeddingMs', 'llmMs', 'retrievalMs', 'totalMs'],
    );
  });

  it('feeds each passage to the LLM, not the whole document', async () => {
    await readAllParts(await createChatStream([userMessage(QUESTION)], NOT_ABORTED));

    expect(opensearch.search).toHaveBeenCalledWith(QUESTION, EMBEDDING, 0);
    expect(mongo.fetchParentDocuments).toHaveBeenCalledWith([SECTION.identifier, DOCUMENT.identifier]);

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
      new RagError('embedding', 'EMBEDDING_FAILED', 'Failed to generate embeddings: ECONNREFUSED'),
    );

    const parts = await readAllParts(await createChatStream([userMessage(QUESTION)], NOT_ABORTED));

    expect(parts[parts.length - 1]).toEqual({
      type: 'error',
      errorText: serializeChatError({ stage: 'embedding', code: 'EMBEDDING_FAILED' }),
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
