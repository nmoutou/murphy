import type { InferUIMessageChunk, UIMessageStreamWriter } from 'ai';
import type { AppUIMessage, AppMessageMetadata, RagTiming } from '@murphy/contract/messages';
import type { ChatMessage } from '../infra/llm';
import type { Passage } from '../types/rag';
import { createUIMessageStream } from 'ai';
import crypto from 'crypto';
import { logger as rootLogger } from '../utils/logger';
import { embedQuestion, retrieveChunks, fetchPassages, buildContextString } from './ragService';
import { getInfraClients } from '../infra/clients';
import { RagError, serializeDocumentKey, toChatError } from '../types/rag';
import { serializeChatError } from '@murphy/contract/errors';
import { config } from '../config';

const logger = rootLogger.child({ context: 'chatService' });

type AppWriter = UIMessageStreamWriter<AppUIMessage>;

export const extractQuestionFromMessages = (messages: AppUIMessage[]): string => {
  const lastUser = [...messages].reverse().find((msg) => msg.role === 'user');
  if (!lastUser) return '';

  return lastUser.parts
    .map((part) => (part.type === 'text' ? part.text : ''))
    .join('');
};

const writeParentDocument = (writer: AppWriter, { document, chunk }: Passage): void => {
  writer.write({
    type: 'data-parentDocument',
    data: { identifier: document.identifier, title: document.title, type: chunk.type, content: document.content },
  });
};

/**
 * Writes the sources in ranking order: a parent document once, before its first
 * passage, then each passage with its highlight bounds (ADR-039 §5)
 */
const writeSources = (writer: AppWriter, passages: readonly Passage[]): void => {
  const writtenDocuments = new Set<string>();
  for (const passage of passages) {
    const documentKey = serializeDocumentKey(passage.document);
    if (!writtenDocuments.has(documentKey)) {
      writeParentDocument(writer, passage);
      writtenDocuments.add(documentKey);
    }
    const { chunk, document, highlightStart, highlightEnd } = passage;
    writer.write({
      type: 'data-document',
      data: {
        chunkId: chunk.chunkId,
        identifier: document.identifier,
        highlightStart,
        highlightEnd,
        score: chunk.score,
        title: document.title,
        type: chunk.type,
      },
    });
  }
};

const buildLlmMessages = (question: string, passages: readonly Passage[]): ChatMessage[] => [
  { role: 'system', content: `${config.llm.systemPrompt}\n\nContexte:\n${buildContextString(passages)}` },
  { role: 'user', content: question },
];

const ABORTED_BY_CLIENT = 'Chat stream aborted by the client';

/** Embeds the question, finds and reads its passages, then writes them as sources */
const retrieveSources = async (writer: AppWriter, question: string) => {
  const { embedding, embeddingMs } = await embedQuestion(question);
  const { chunks, retrievalMs } = await retrieveChunks(embedding, config.retrieval.topK);
  // The title and the text live in the parent documents: read them before the sources
  const { passages, docFetchMs } = await fetchPassages(chunks);
  writeSources(writer, passages);
  return { passages, timing: { embeddingMs, retrievalMs, docFetchMs } };
};

/**
 * @returns the LLM duration, or `undefined` once the failure is written as an `error` part
 */
const streamAnswer = async (
  writer: AppWriter,
  messageId: string,
  messages: ChatMessage[],
  abortSignal: AbortSignal,
): Promise<number | undefined> => {
  const llmStart = Date.now();
  try {
    for await (const token of getInfraClients().llm.stream(messages, abortSignal)) {
      writer.write({ type: 'text-delta', id: messageId, delta: token });
    }
  } catch (error) {
    writer.write({ type: 'error', errorText: serializeChatError(toChatError(error)) });
    return undefined;
  }
  return Date.now() - llmStart;
};

const writeFinish = (writer: AppWriter, messageId: string, ragTiming: RagTiming): void => {
  writer.write({ type: 'text-end', id: messageId });
  writer.write({
    type: 'finish',
    finishReason: 'stop',
    messageMetadata: { ragTiming } satisfies AppMessageMetadata,
  });
};

/** The client is gone: nothing more is written, and the next stages do not run */
const isAbortedByClient = (abortSignal: AbortSignal): boolean => {
  if (abortSignal.aborted) logger.info(ABORTED_BY_CLIENT);
  return abortSignal.aborted;
};

/**
 * The RAG pipeline as a stream of UI message parts
 * @param abortSignal raised when the client leaves: the pipeline stops before or during the LLM
 * @throws RagError with stage='request' when the last user message has no text
 */
export const createChatStream = async (
  uiMessages: AppUIMessage[],
  abortSignal: AbortSignal,
): Promise<ReadableStream<InferUIMessageChunk<AppUIMessage>>> => {
  const question = extractQuestionFromMessages(uiMessages);
  if (!question.trim()) {
    throw new RagError('request', 'NO_QUESTION', 'No question provided');
  }

  const messageId = crypto.randomUUID();
  const startTime = Date.now();

  return createUIMessageStream<AppUIMessage>({
    execute: async ({ writer }) => {
      writer.write({ type: 'start', messageId });
      writer.write({ type: 'text-start', id: messageId });

      const { passages, timing } = await retrieveSources(writer, question);
      if (isAbortedByClient(abortSignal)) return;

      const llmMs = await streamAnswer(writer, messageId, buildLlmMessages(question, passages), abortSignal);
      if (llmMs === undefined || isAbortedByClient(abortSignal)) return;

      writeFinish(writer, messageId, { ...timing, llmMs, totalMs: Date.now() - startTime });
      logger.info({ questionLength: question.length, totalMs: Date.now() - startTime }, 'Chat stream finished');
    },
    onError: (err) => {
      logger.error({ err }, 'Chat stream failed');
      return serializeChatError(toChatError(err));
    },
  });
};
