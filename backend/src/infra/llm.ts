import type { LanguageModel } from 'ai';
import type { LlmConfig } from '../config';
import { createOpenAICompatible } from '@ai-sdk/openai-compatible';
import { streamText } from 'ai';
import { logger as rootLogger } from '../utils/logger';
import { RagError } from '../types/rag';

const logger = rootLogger.child({ context: 'llm' });

/** Un nom interne au SDK, pas un fournisseur : l'URL seule désigne le serveur */
const PROVIDER_NAME = 'llm';
/** ADR-010 : aucune nouvelle tentative automatique */
const NO_RETRY = 0;

export interface LlmMessage {
  readonly role: 'user' | 'assistant';
  readonly content: string;
}

export interface LlmRequest {
  readonly instructions: string;
  readonly messages: readonly LlmMessage[];
  /** Levé, il coupe l'appel : l'itération finit alors sans erreur */
  readonly signal: AbortSignal;
}

export interface LlmUsage {
  readonly inputTokens?: number;
  readonly outputTokens?: number;
}

/** Les fragments du texte ; à la fin, l'usage, quand le serveur le donne */
export type LlmAnswer = AsyncGenerator<string, LlmUsage | undefined, undefined>;

export interface LlmClient {
  /** @throws RagError `LLM_FAILED` pendant l'itération, si le serveur échoue */
  streamAnswer(request: LlmRequest): LlmAnswer;
}

const readField = (error: unknown, field: string): unknown =>
  typeof error === 'object' && error !== null ? Reflect.get(error, field) : undefined;

/** Ni le message ni le corps : ils peuvent reprendre une part de la requête */
const toLlmFailure = (error: unknown): RagError => {
  const errorName = String(readField(error, 'name') ?? 'unknown');
  const statusCode = readField(error, 'statusCode');
  logger.error({ errorName, statusCode }, 'LLM call failed');
  return new RagError('generation', 'LLM_FAILED', `LLM call failed: ${errorName}, status ${String(statusCode)}`);
};

/** Un serveur compatible OpenAI, par l'AI SDK : changer de serveur change l'URL, pas le code */
export class AiSdkLlmClient implements LlmClient {
  constructor(
    private readonly model: LanguageModel,
    private readonly maxOutputTokens: number,
  ) {}

  async *streamAnswer({ instructions, messages, signal }: LlmRequest): LlmAnswer {
    const result = streamText({
      model: this.model,
      system: instructions,
      messages: messages.map(({ role, content }) => ({ role, content })),
      maxOutputTokens: this.maxOutputTokens,
      maxRetries: NO_RETRY,
      abortSignal: signal,
      // Sans lui, le SDK écrit l'erreur entière dans la console
      onError: () => undefined,
    });
    let usage: LlmUsage | undefined;
    for await (const part of result.fullStream) {
      if (part.type === 'text-delta') yield part.text;
      else if (part.type === 'finish') usage = part.totalUsage;
      else if (part.type === 'error' && !signal.aborted) throw toLlmFailure(part.error);
    }
    return usage;
  }
}

export const createLlmClient = ({ baseUrl, apiKey, model, maxOutputTokens }: LlmConfig): LlmClient => {
  const provider = createOpenAICompatible({ name: PROVIDER_NAME, baseURL: baseUrl, apiKey });
  return new AiSdkLlmClient(provider(model), maxOutputTokens);
};
