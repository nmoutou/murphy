import type { AppUIMessage, AppMessageMetadata } from '../types/messages';
import { createUIMessageStream } from 'ai';
import crypto from 'crypto';
import { logger as rootLogger } from '../utils/logger';
import {
  embedQuestion,
  retrieveChunks,
  fetchChunkDocuments,
  buildContextString,
} from './ragService';
import { getInfraClients } from '../infra/clients';
import { config } from '../config';

const logger = rootLogger.child({ context: 'chatService' });

export const extractQuestionFromMessages = (messages: AppUIMessage[]): string => {
  const lastUser = [...messages].reverse().find((msg) => msg.role === 'user');
  if (!lastUser) return '';

  return lastUser.parts
    .map((part) => (part.type === 'text' ? part.text : ''))
    .join('');
};

export async function createChatStream(uiMessages: AppUIMessage[]) {
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

      // Stage 1 — Embedding
      const { embedding, embeddingMs } = await embedQuestion(question);

      // Stage 2 — Qdrant search
      const { results, retrievalMs } = await retrieveChunks(embedding, config.retrieval.topK);

      // Stream document references immediately (before LLM)
      for (const result of results) {
        if (result.payload?.chunkId) {
          writer.write({
            type: 'data-document',
            data: {
              chunkId: result.payload.chunkId as string,
              title: result.payload.title as string | undefined,
              type: result.payload.type as string | undefined,
              score: result.similarity,
            },
          });
        }
      }

      // Stage 3 — Fetch MongoDB content (for LLM context only)
      const chunkIds = results
        .map((r) => r.payload?.chunkId as string | undefined)
        .filter((id): id is string => !!id);
      const { documents, docFetchMs } = await fetchChunkDocuments(chunkIds);

      // Stage 4 — Stream LLM
      const context = buildContextString(documents);
      const systemPromptText = `${config.llm.systemPrompt}\n\nContexte:\n${context}`;
      const llmMessages = [
        { role: 'system' as const, content: systemPromptText },
        { role: 'user' as const, content: question },
      ];

      const llmStart = Date.now();
      try {
        for await (const token of getInfraClients().llm.stream(llmMessages)) {
          writer.write({ type: 'text-delta', id: messageId, delta: token });
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        writer.write({ type: 'error', errorText: errorMessage });
        return;
      }

      const llmMs = Date.now() - llmStart;
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

