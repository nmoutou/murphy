import type { InferUIMessageChunk, UIMessageStreamWriter } from 'ai';
import type { AppUIMessage, AppMessageMetadata, RagTiming } from '@murphy/contract/messages';
import type { ChatMessage } from '../infra/llm';
import type { FoundDocument, Passage } from '../types/rag';
import { createUIMessageStream } from 'ai';
import crypto from 'crypto';
import { logger as rootLogger } from '../utils/logger';
import { embedQuestion, retrieveDocuments, fetchDocuments, buildContextString } from './ragService';
import { getInfraClients } from '../infra/clients';
import { RagError, toChatError } from '../types/rag';
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

const writeParentDocument = (writer: AppWriter, { document, documentType, nature }: FoundDocument): void => {
  writer.write({
    type: 'data-parentDocument',
    data: { identifier: document.identifier, title: document.title, documentType, nature, content: document.content },
  });
};

const writePassage = (writer: AppWriter, { document, documentType, nature }: FoundDocument, passage: Passage): void => {
  writer.write({
    type: 'data-document',
    data: {
      chunkId: passage.ref.chunkId,
      identifier: document.identifier,
      highlightStart: passage.highlightStart,
      highlightEnd: passage.highlightEnd,
      title: document.title,
      documentType,
      nature,
    },
  });
};

/**
 * Dans l'ordre du classement, chaque document puis ses passages. Une section n'a aucun
 * passage : le frontend ne l'affiche pas encore (ADR-028 §10)
 */
const writeSources = (writer: AppWriter, documents: readonly FoundDocument[]): void => {
  for (const found of documents) {
    writeParentDocument(writer, found);
    for (const passage of found.passages) writePassage(writer, found, passage);
  }
};

const buildLlmMessages = (question: string, documents: readonly FoundDocument[]): ChatMessage[] => [
  { role: 'system', content: `${config.llm.systemPrompt}\n\nContexte:\n${buildContextString(documents)}` },
  { role: 'user', content: question },
];

const ABORTED_BY_CLIENT = 'Chat stream aborted by the client';

const retrieveSources = async (writer: AppWriter, question: string) => {
  const { embedding, embeddingMs } = await embedQuestion(question);
  const { documents: retrieved, retrievalMs } = await retrieveDocuments(question, embedding);
  // Titre et texte vivent dans Mongo : les lire avant d'écrire les sources
  const { documents, docFetchMs } = await fetchDocuments(retrieved);
  writeSources(writer, documents);
  return { documents, timing: { embeddingMs, retrievalMs, docFetchMs } };
};

/**
 * @returns la durée du LLM, ou `undefined` une fois l'échec écrit en part `error`
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

/** Client parti : plus rien n'est écrit et les étapes suivantes ne tournent pas */
const isAbortedByClient = (abortSignal: AbortSignal): boolean => {
  if (abortSignal.aborted) logger.info(ABORTED_BY_CLIENT);
  return abortSignal.aborted;
};

/**
 * Le pipeline RAG, en flux de parts de message
 * @param abortSignal levé au départ du client : le pipeline s'arrête avant ou pendant le LLM
 * @throws RagError d'étape `request` si le dernier message utilisateur n'a pas de texte
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

      const { documents, timing } = await retrieveSources(writer, question);
      if (isAbortedByClient(abortSignal)) return;

      const llmMs = await streamAnswer(writer, messageId, buildLlmMessages(question, documents), abortSignal);
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
