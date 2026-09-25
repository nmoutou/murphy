import type { InferUIMessageChunk, UIMessageStreamWriter } from 'ai';
import type { AppUIMessage, AppMessageMetadata } from '@murphy/contract/messages';
import type { ChatMessage } from '../infra/llm';
import type { Passage } from '../types/rag';
import { createUIMessageStream } from 'ai';
import crypto from 'crypto';
import { logger as rootLogger } from '../utils/logger';
import { embedQuestion, retrieveChunks, fetchPassages, buildContextString } from './ragService';
import { getInfraClients } from '../infra/clients';
import { serializeDocumentKey } from '../types/rag';
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

/**
 * @returns the LLM duration, or `undefined` once the failure is written as an `error` part
 */
const streamAnswer = async (writer: AppWriter, messageId: string, messages: ChatMessage[]): Promise<number | undefined> => {
  const llmStart = Date.now();
  try {
    for await (const token of getInfraClients().llm.stream(messages)) {
      writer.write({ type: 'text-delta', id: messageId, delta: token });
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    writer.write({ type: 'error', errorText: errorMessage });
    return undefined;
  }
  return Date.now() - llmStart;
};

export async function createChatStream(uiMessages: AppUIMessage[]): Promise<ReadableStream<InferUIMessageChunk<AppUIMessage>>> {
  const question = extractQuestionFromMessages(uiMessages);

  if (!question.trim()) {
    throw new Error('No question provided');
  }

  const messageId = crypto.randomUUID();
  const startTime = Date.now();

  return createUIMessageStream<AppUIMessage>({
    execute: async ({ writer }) => {
      writer.write({ type: 'start', messageId });
      writer.write({ type: 'text-start', id: messageId });

      const { embedding, embeddingMs } = await embedQuestion(question);
      const { chunks, retrievalMs } = await retrieveChunks(embedding, config.retrieval.topK);
      // The title and the text live in the parent documents: read them before the sources
      const { passages, docFetchMs } = await fetchPassages(chunks);
      writeSources(writer, passages);

      const llmMs = await streamAnswer(writer, messageId, buildLlmMessages(question, passages));
      if (llmMs === undefined) return;

      writer.write({ type: 'text-end', id: messageId });
      writer.write({
        type: 'finish',
        finishReason: 'stop',
        messageMetadata: {
          ragTiming: { embeddingMs, retrievalMs, docFetchMs, llmMs, totalMs: Date.now() - startTime },
        } satisfies AppMessageMetadata,
      });

      logger.info({ questionLength: question.length, totalMs: Date.now() - startTime }, 'Chat stream finished');
    },
    onError: (err) => {
      const msg = err instanceof Error ? err.message : String(err);
      logger.error({ err }, 'Chat stream failed');
      return msg;
    },
  });
}
