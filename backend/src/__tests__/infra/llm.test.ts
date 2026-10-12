import type { LanguageModelV3StreamPart } from '@ai-sdk/provider';
import { simulateReadableStream } from 'ai';
import { MockLanguageModelV3 } from 'ai/test';
import { AiSdkLlmClient } from '../../infra/llm';

const mockError = jest.fn();

jest.mock('../../utils/logger', () => {
  const logger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: (...args: unknown[]) => mockError(...args), child: () => logger };
  return { logger };
});

const MAX_OUTPUT_TOKENS = 2_000;
const PROMPT_SECRET = 'question confidentielle';

const textParts = (fragments: readonly string[]): LanguageModelV3StreamPart[] => [
  { type: 'stream-start', warnings: [] },
  { type: 'text-start', id: '1' },
  ...fragments.map((delta): LanguageModelV3StreamPart => ({ type: 'text-delta', id: '1', delta })),
  { type: 'text-end', id: '1' },
  {
    type: 'finish',
    finishReason: { unified: 'stop', raw: 'stop' },
    usage: {
      inputTokens: { total: 12, noCache: undefined, cacheRead: undefined, cacheWrite: undefined },
      outputTokens: { total: 3, text: undefined, reasoning: undefined },
    },
  },
];

const modelStreaming = (fragments: readonly string[], chunkDelayInMs: number | null = null) =>
  new MockLanguageModelV3({
    doStream: async () => ({ stream: simulateReadableStream({ chunks: textParts(fragments), chunkDelayInMs }) }),
  });

const collect = async (answer: AsyncGenerator<string, unknown>) => {
  const fragments: string[] = [];
  let next = await answer.next();
  while (!next.done) {
    fragments.push(next.value);
    next = await answer.next();
  }
  return { fragments, returned: next.value };
};

const REQUEST = { instructions: 'Explique.', messages: [{ role: 'user' as const, content: PROMPT_SECRET }] };

describe('AiSdkLlmClient.streamAnswer', () => {
  it('yields the text fragments, then returns the usage', async () => {
    const model = modelStreaming(['Bon', 'jour']);
    const client = new AiSdkLlmClient(model, MAX_OUTPUT_TOKENS);

    const { fragments, returned } = await collect(client.streamAnswer({ ...REQUEST, signal: new AbortController().signal }));

    expect(fragments).toEqual(['Bon', 'jour']);
    expect(returned).toMatchObject({ inputTokens: 12, outputTokens: 3 });
    expect(model.doStreamCalls[0]).toMatchObject({ maxOutputTokens: MAX_OUTPUT_TOKENS });
  });

  it('ends without error when the caller aborts', async () => {
    const controller = new AbortController();
    const client = new AiSdkLlmClient(modelStreaming(['a', 'b', 'c', 'd'], 20), MAX_OUTPUT_TOKENS);
    const answer = client.streamAnswer({ ...REQUEST, signal: controller.signal });

    await answer.next();
    controller.abort();

    await expect(collect(answer)).resolves.toBeDefined();
  });

  it('fails with LLM_FAILED, logging the status and the name of the error but never its message', async () => {
    const failure = Object.assign(new Error(`401 refused: ${PROMPT_SECRET}`), { name: 'AI_APICallError', statusCode: 401 });
    const model = new MockLanguageModelV3({ doStream: async () => { throw failure; } });
    const client = new AiSdkLlmClient(model, MAX_OUTPUT_TOKENS);

    const answer = client.streamAnswer({ ...REQUEST, signal: new AbortController().signal });

    await expect(answer.next()).rejects.toMatchObject({ stage: 'generation', code: 'LLM_FAILED' });
    expect(mockError).toHaveBeenCalledWith({ errorName: 'AI_APICallError', statusCode: 401 }, 'LLM call failed');
    expect(JSON.stringify(mockError.mock.calls)).not.toContain(PROMPT_SECRET);
  });

  it('never retries a failed call', async () => {
    const model = new MockLanguageModelV3({
      doStream: async () => { throw Object.assign(new Error('busy'), { name: 'AI_APICallError', statusCode: 503, isRetryable: true }); },
    });
    const client = new AiSdkLlmClient(model, MAX_OUTPUT_TOKENS);

    await expect(client.streamAnswer({ ...REQUEST, signal: new AbortController().signal }).next()).rejects.toBeDefined();
    expect(model.doStreamCalls).toHaveLength(1);
  });
});
