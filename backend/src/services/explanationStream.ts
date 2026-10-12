import type { ServerResponse } from 'http';
import type { UIMessageStreamWriter } from 'ai';
import type { LlmUsage } from '../infra/llm';
import type { OpenedAnswer, PreparedExplanation } from './explanationService';
import { randomUUID } from 'crypto';
import { createUIMessageStream, pipeUIMessageStreamToResponse } from 'ai';
import { logger as rootLogger } from '../utils/logger';
import { toErrorResponse } from '../utils/errorResponse';

const logger = rootLogger.child({ context: 'explanationStream' });

type Outcome = 'completed' | 'aborted' | 'error';

interface StreamedAnswer {
  readonly answerLength: number;
  readonly usage?: LlmUsage;
}

export interface ExplanationStream {
  readonly response: ServerResponse;
  readonly prepared: PreparedExplanation;
  readonly opened: OpenedAnswer;
  /** Levé quand le client part : le LLM est déjà coupé, l'itération finit */
  readonly signal: AbortSignal;
}

const isUsage = (value: unknown): value is LlmUsage => typeof value === 'object' && value !== null;

/** @throws RagError `LLM_FAILED` si le LLM échoue en cours de route */
const writeAnswer = async (writer: UIMessageStreamWriter, { first, rest }: OpenedAnswer): Promise<StreamedAnswer> => {
  const id = randomUUID();
  writer.write({ type: 'start', messageId: id });
  writer.write({ type: 'text-start', id });
  let answerLength = 0;
  let next = first;
  while (!next.done) {
    writer.write({ type: 'text-delta', id, delta: next.value });
    answerLength += next.value.length;
    next = await rest.next();
  }
  writer.write({ type: 'text-end', id });
  writer.write({ type: 'finish' });
  return { answerLength, usage: isUsage(next.value) ? next.value : undefined };
};

/**
 * Ni question, ni réponse, ni texte : des longueurs, une durée, l'issue et les tokens
 * (ADR-033 §14)
 */
const logOutcome = (prepared: PreparedExplanation, outcome: Outcome, answer: StreamedAnswer, startTime: number): void => {
  const { documentCount, contextLength } = prepared;
  logger.info(
    {
      documentCount,
      contextLength,
      answerLength: answer.answerLength,
      inputTokens: answer.usage?.inputTokens,
      outputTokens: answer.usage?.outputTokens,
      outcome,
      durationMs: Date.now() - startTime,
    },
    'Explanation completed',
  );
};

/**
 * La réponse en flux SSE de l'AI SDK. Une erreur en cours de route, le statut 200 déjà
 * parti, devient un événement d'erreur qui ne porte que son code.
 */
export const streamExplanation = ({ response, prepared, opened, signal }: ExplanationStream): void => {
  const startTime = Date.now();
  const stream = createUIMessageStream({
    execute: async ({ writer }) => {
      let answer: StreamedAnswer = { answerLength: 0 };
      let outcome: Outcome = 'error';
      try {
        answer = await writeAnswer(writer, opened);
        outcome = signal.aborted ? 'aborted' : 'completed';
      } finally {
        logOutcome(prepared, outcome, answer, startTime);
      }
    },
    onError: (error) => toErrorResponse(error).code,
  });
  // Le statut 200 est parti : un échec d'écriture ne peut plus que se journaliser
  pipeUIMessageStreamToResponse({ response, stream }).catch((error: unknown) => {
    logger.error({ err: error }, 'Explanation stream could not be written');
  });
};
