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
  top_p?: number;
  frequency_penalty?: number;
}

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
   * Shared HTTP request logic: builds payload, fires fetch with timeout, checks status.
   * @throws Error (plain) on HTTP error — callers wrap into RagError
   */
  private async _doRequest(messages: ChatMessage[], stream: boolean): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const payload: ChatCompletionPayload = {
        model: this.model,
        messages,
        temperature: this.temperature,
        max_tokens: this.maxTokens,
        stream,
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
   * Stream completions from Mammouth API
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

      const response = await this._doRequest(messages, true);

      if (!response.body) {
        throw new Error('No response body from LLM API');
      }

      // Process streaming response
      const reader = response.body as any;
      let buffer = '';

      for await (const chunk of reader) {
        // Decode chunk to string correctly for Buffer / Uint8Array
        let chunkStr: string;
        try {
          if (typeof chunk === 'string') {
            chunkStr = chunk;
          } else if (typeof Buffer !== 'undefined' && Buffer.isBuffer(chunk)) {
            chunkStr = (chunk as Buffer).toString('utf8');
          } else if (chunk instanceof Uint8Array) {
            chunkStr = new TextDecoder().decode(chunk as Uint8Array);
          } else {
            chunkStr = String(chunk);
          }
        } catch (e) {
          chunkStr = String(chunk);
        }

        buffer += chunkStr;
        const lines = buffer.split('\n');

        // Process all complete lines
        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim();

          if (!line) continue;

          // Support both SSE "data: ..." and raw JSON lines
          const data = line.startsWith('data: ') ? line.slice(6) : line;

          if (data === '[DONE]') {
            logger.debug('LLM stream completed');
            continue;
          }

          try {
            const json = JSON.parse(data);

            // Support multiple possible streaming token fields used by different APIs
            const delta = json.choices?.[0]?.delta ?? {};
            const token = (delta?.content as string) || (delta?.text as string) || (json.choices?.[0]?.text?.content as string) || '';

            if (token) {
              yield token;
            }
          } catch (e) {
            // Ignore invalid JSON lines
          }
        }

        // Keep incomplete line in buffer
        buffer = lines[lines.length - 1];
      }

      const duration = Date.now() - startTime;
      logger.debug({ durationMs: duration }, 'LLM stream finished');
    } catch (error) {
      const duration = Date.now() - startTime;
      const errorMessage = error instanceof Error ? error.message : String(error);

      logger.error(
        { errorMessage, errorType: (error as any)?.name, durationMs: duration },
        'LLM stream failed'
      );

      throw new RagError(
        'llm',
        errorMessage.includes('abort') ? 'TIMEOUT' : 'API_ERROR',
        `Failed to stream LLM response: ${errorMessage}`,
      );
    }
  }

  /**
   * Non-streaming completion
   * @param messages Chat messages
   * @returns Full completion text
   * @throws RagError with stage='llm'
   */
  async complete(messages: ChatMessage[]): Promise<string> {
    const startTime = Date.now();

    try {
      logger.info(
        { model: this.model, messageCount: messages.length },
        'LLM completion request started'
      );

      const response = await this._doRequest(messages, false);
      const data = (await response.json()) as any;
      const content = data.choices?.[0]?.message?.content || '';

      const duration = Date.now() - startTime;
      logger.info({ durationMs: duration }, 'LLM completion finished');

      return content;
    } catch (error) {
      const duration = Date.now() - startTime;
      const errorMessage = error instanceof Error ? error.message : String(error);

      logger.error(
        { errorMessage, durationMs: duration },
        'LLM completion failed'
      );

      throw new RagError(
        'llm',
        errorMessage.includes('abort') ? 'TIMEOUT' : 'API_ERROR',
        `Failed to get LLM completion: ${errorMessage}`,
      );
    }
  }

  /**
   * Get provider configuration (for logging/debugging)
   */
  getConfig() {
    return {
      model: this.model,
      temperature: this.temperature,
      maxTokens: this.maxTokens,
      timeoutMs: this.timeoutMs,
      apiUrl: this.apiUrl,
    };
  }
}
