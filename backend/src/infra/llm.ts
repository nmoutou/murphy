/**
 * LLM Provider
 * OpenAI-compatible provider with streaming support
 */

import { logger } from '../utils/logger';
import { RagError } from '../types/rag';

interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

interface ChatCompletionPayload {
  model: string;
  messages: ChatMessage[];
  temperature: number;
  max_tokens: number;
  stream: boolean;
}

/** One streamed chunk, in the shapes the accepted OpenAI-compatible APIs send. */
interface ChatCompletionChunk {
  choices?: Array<{
    delta?: { content?: string; text?: string };
    text?: { content?: string };
  }>;
}

const SSE_DATA_PREFIX = 'data: ';
const SSE_DONE_MARKER = '[DONE]';

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

  const choice = chunk?.choices?.[0];
  return choice?.delta?.content || choice?.delta?.text || choice?.text?.content || '';
};

export class LLMProvider {
  private readonly apiUrl: string;
  private readonly apiKey: string;
  private readonly model: string;
  private readonly temperature: number;
  private readonly maxTokens: number;
  private readonly timeoutMs: number;

  constructor(
    apiUrl: string = process.env.LLM_API_ENDPOINT || '',
    apiKey: string = process.env.LLM_API_KEY || '',
    model: string = process.env.LLM_MODEL || '',
    temperature: number = parseFloat(process.env.LLM_TEMPERATURE || '0.7'),
    maxTokens: number = parseInt(process.env.LLM_MAX_TOKENS || '1000', 10),
    timeoutMs: number = parseInt(process.env.LLM_TIMEOUT || '30000', 10)
  ) {
    if (!apiKey) {
      logger.warn('LLM_API_KEY not configured');
    }
    this.apiUrl = apiUrl;
    this.apiKey = apiKey;
    this.model = model;
    this.temperature = temperature;
    this.maxTokens = maxTokens;
    this.timeoutMs = timeoutMs;
  }

  /**
   * Fires the streaming request with a timeout and checks the HTTP status.
   * @throws Error (plain) on HTTP error — the caller wraps it into RagError
   */
  private async _doRequest(messages: ChatMessage[]): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const payload: ChatCompletionPayload = {
        model: this.model,
        messages,
        temperature: this.temperature,
        max_tokens: this.maxTokens,
        stream: true,
      };

      const response = await fetch(this.apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${this.apiKey}`,
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`LLM API returned ${response.status}: ${response.statusText}`);
      }

      return response;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * Stream completions from the configured OpenAI-compatible API
   * @param messages Chat messages (system + user)
   * @returns Async iterator for streaming tokens
   * @throws RagError with stage='llm'
   */
  async *stream(messages: ChatMessage[]): AsyncGenerator<string, void, unknown> {
    const startTime = Date.now();

    try {
      logger.debug(
        { model: this.model, messageCount: messages.length, temperature: this.temperature },
        'LLM stream request started'
      );

      const response = await this._doRequest(messages);

      if (!response.body) {
        throw new Error('No response body from LLM API');
      }

      // Streaming decoder: a multi-byte character split across two network chunks
      // (an accented letter, say) is decoded once both halves have arrived.
      const text = response.body.pipeThrough(new TextDecoderStream());
      let buffer = '';

      for await (const piece of text) {
        buffer += piece;
        const lines = buffer.split('\n');
        // The last element is an incomplete line: keep it for the next piece
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          const token = extractToken(line);
          if (token) yield token;
        }
      }

      logger.debug({ durationMs: Date.now() - startTime }, 'LLM stream finished');
    } catch (error) {
      const duration = Date.now() - startTime;
      const errorMessage = error instanceof Error ? error.message : String(error);

      logger.error(
        { errorMessage, errorType: error instanceof Error ? error.name : undefined, durationMs: duration },
        'LLM stream failed'
      );

      throw new RagError(
        'llm',
        errorMessage.includes('abort') ? 'TIMEOUT' : 'API_ERROR',
        `Failed to stream LLM response: ${errorMessage}`,
      );
    }
  }
}
