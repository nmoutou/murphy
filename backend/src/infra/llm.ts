import type { LlmConfig } from '../config';
import type { RagFailure } from '../types/rag';
import { logger as rootLogger } from '../utils/logger';
import { toRagError } from '../types/rag';

const logger = rootLogger.child({ context: 'llm' });

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

/** `content` est null sur certains morceaux (fin de réponse) */
interface ChatCompletionChunk {
  choices?: Array<{ delta?: { content?: string | null } }>;
}

const SSE_DATA_PREFIX = 'data: ';
const SSE_DONE_MARKER = '[DONE]';
const LINE_SEPARATOR = '\n';
/** Le nom de l'erreur d'`AbortSignal.timeout` : `toRagError` la classe en timeout */
const TIMEOUT_ERROR_NAME = 'TimeoutError';
const LLM_FAILURE: RagFailure = { stage: 'llm', code: 'API_ERROR', operation: 'stream LLM response' };

/** Le prompt système ne regarde pas le provider : `chatService` construit les messages */
export type LLMProviderOptions = Omit<LlmConfig, 'systemPrompt'>;

/**
 * Jeton d'une ligne du flux (SSE `data: …` ou JSON brut). Lignes vides, marqueur de
 * fin et lignes non JSON donnent ''.
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
 * Lignes complètes d'un flux texte. Une ligne coupée entre deux morceaux sort une fois
 * entière ; un dernier morceau sans saut de ligne final est perdu.
 */
async function* readLines(text: AsyncIterable<string>): AsyncGenerator<string, void, undefined> {
  let buffer = '';
  for await (const piece of text) {
    buffer += piece;
    const lines = buffer.split(LINE_SEPARATOR);
    buffer = lines.pop() ?? '';
    yield* lines;
  }
}

export class LLMProvider {
  constructor(private readonly settings: LLMProviderOptions) {}

  /**
   * Le timeout ne couvre que l'attente de la réponse, pas le streaming qui suit : d'où
   * un contrôleur annulé à réception plutôt qu'`AbortSignal.timeout`, qui couperait une
   * longue réponse. Le signal de l'appelant couvre les deux.
   * @throws Error simple (timeout, erreur HTTP, corps absent) — `stream` l'enveloppe
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
   * @param abortSignal une fois levé, la requête est coupée et l'itérateur finit sans erreur
   * @throws RagError d'étape `llm`
   */
  async *stream(messages: ChatMessage[], abortSignal?: AbortSignal): AsyncGenerator<string, void, unknown> {
    const startTime = Date.now();
    const { model, temperature } = this.settings;
    logger.debug({ model, messageCount: messages.length, temperature }, 'LLM stream request started');

    try {
      const body = await this.openStream(messages, abortSignal);
      // Décodeur en flux : un caractère multi-octets coupé entre deux paquets (une
      // lettre accentuée) n'est décodé qu'une fois entier.
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
