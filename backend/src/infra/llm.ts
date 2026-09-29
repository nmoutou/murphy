/**
 * LLM Provider
 * OpenAI-compatible provider with streaming support
 */

import type { LlmConfig } from '../config';
import type { RagFailure } from '../types/rag';
import { logger } from '../utils/logger';
import { toRagError } from '../types/rag';

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

interface ChatCompletionPayload {
  model: string;
  messages: ChatMessage[];
  temperature: number;
  stream: boolean;
}

/** One streamed chunk of an OpenAI-compatible API; `content` is null on some chunks (end of answer) */
interface ChatCompletionChunk {
  choices?: Array<{ delta?: { content?: string | null } }>;
}

const SSE_DATA_PREFIX = 'data: ';
const SSE_DONE_MARKER = '[DONE]';
const LINE_SEPARATOR = '\n';
/** Named like the error of `AbortSignal.timeout`, so that `toRagError` classifies it as a timeout */
const TIMEOUT_ERROR_NAME = 'TimeoutError';
const LLM_FAILURE: RagFailure = { stage: 'llm', code: 'API_ERROR', operation: 'stream LLM response' };

/** The system prompt is not the provider's business: the pipeline (`chatService`) builds the messages */
export type LLMProviderOptions = Omit<LlmConfig, 'systemPrompt'>;

/**
 * Token carried by one line of the stream (SSE `data: …` or raw JSON line).
 * Blank lines, the end marker and non-JSON lines carry none: they yield ''.
 */
const extractToken = (rawLine: string): string => {
  const line = rawLine.trim();
  if (!line) return '';

  const data = line.startsWith(SSE_DATA_PREFIX) ? line.slice(SSE_DATA_PREFIX.length) : line;
  if (data === SSE_DONE_MARKER) {
    logger.debug('LLM stream completed');
    return '';
  }

  let chunk: ChatCompletionChunk | null;
  try {
    chunk = JSON.parse(data);
  } catch {
    logger.debug({ line: data }, 'Ignoring non-JSON line in LLM stream');
    return '';
  }

  return chunk?.choices?.[0]?.delta?.content ?? '';
};

/**
 * Complete lines of a text stream. A line split across two pieces is emitted
 * once whole; a last piece without a final newline is dropped.
 */
async function* readLines(text: AsyncIterable<string>): AsyncGenerator<string, void, undefined> {
  let buffer = '';
  for await (const piece of text) {
    buffer += piece;
    const lines = buffer.split(LINE_SEPARATOR);
    // The last element is an incomplete line: keep it for the next piece
    buffer = lines.pop() ?? '';
    yield* lines;
  }
}

export class LLMProvider {
  constructor(private readonly settings: LLMProviderOptions) {}

  /**
   * Fires the streaming request and returns the response body.
   *
   * The timeout covers the wait for the response only, not the streaming of the
   * answer that follows: hence a controller cleared once the response is there,
   * not `AbortSignal.timeout`, which would also cut a long answer. The caller's
   * signal covers both: the request, then the body read under the same `fetch`.
   * @throws Error (plain) on timeout, HTTP error or missing body — `stream` wraps it
   */
  private async openStream(messages: ChatMessage[], abortSignal?: AbortSignal): Promise<NonNullable<Response['body']>> {
    const { apiUrl, apiKey, model, temperature, timeoutMs } = this.settings;
    const controller = new AbortController();
    const timeoutId = setTimeout(
      () => controller.abort(new DOMException(`LLM API did not answer within ${timeoutMs} ms`, TIMEOUT_ERROR_NAME)),
      timeoutMs,
    );

    try {
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
        body: JSON.stringify({ model, messages, temperature, stream: true } satisfies ChatCompletionPayload),
        signal: abortSignal ? AbortSignal.any([controller.signal, abortSignal]) : controller.signal,
      });

      if (!response.ok) throw new Error(`LLM API returned ${response.status}: ${response.statusText}`);
      if (!response.body) throw new Error('No response body from LLM API');
      return response.body;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * Stream completions from the configured OpenAI-compatible API
   * @param messages Chat messages (system + user)
   * @param abortSignal once raised, the request is cut and the iterator ends without error
   * @returns Async iterator for streaming tokens
   * @throws RagError with stage='llm'
   */
  async *stream(messages: ChatMessage[], abortSignal?: AbortSignal): AsyncGenerator<string, void, unknown> {
    const startTime = Date.now();
    const { model, temperature } = this.settings;
    logger.debug({ model, messageCount: messages.length, temperature }, 'LLM stream request started');

    try {
      const body = await this.openStream(messages, abortSignal);
      // Streaming decoder: a multi-byte character split across two network chunks
      // (an accented letter, say) is decoded once both halves have arrived.
      for await (const line of readLines(body.pipeThrough(new TextDecoderStream()))) {
        const token = extractToken(line);
        if (token) yield token;
      }
      logger.debug({ durationMs: Date.now() - startTime }, 'LLM stream finished');
    } catch (error) {
      if (abortSignal?.aborted) {
        logger.debug({ durationMs: Date.now() - startTime }, 'LLM stream aborted by the caller');
        return;
      }
      const ragError = toRagError(LLM_FAILURE, error);
      logger.error({ err: error, durationMs: Date.now() - startTime }, ragError.message);
      throw ragError;
    }
  }
}
