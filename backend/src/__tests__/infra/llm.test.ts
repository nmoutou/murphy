import { LLMProvider } from '../../infra/llm';

jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

const MESSAGES = [{ role: 'user' as const, content: 'Quel délai ?' }];
const HTTP_SERVER_ERROR = 500;

const sseLine = (content: string): string => `data: ${JSON.stringify({ choices: [{ delta: { content } }] })}\n`;

const responseOf = (...chunks: Uint8Array[]): Response =>
  new Response(
    new ReadableStream<Uint8Array>({
      start(controller) {
        chunks.forEach((chunk) => controller.enqueue(chunk));
        controller.close();
      },
    }),
  );

const collectTokens = async (tokens: AsyncIterable<string>): Promise<string[]> => {
  const collected: string[] = [];
  for await (const token of tokens) collected.push(token);
  return collected;
};

const createProvider = (): LLMProvider =>
  new LLMProvider({
    apiUrl: 'http://llm.test/v1/chat/completions',
    apiKey: 'test-key',
    model: 'test-model',
    temperature: 0.7,
    timeoutMs: 30_000,
  });

describe('LLMProvider.stream', () => {
  it('yields the delta contents and skips blank lines, the end marker and invalid JSON', async () => {
    const body = `${sseLine('Cinq ')}\n: keep-alive\n${sseLine('ans.')}data: [DONE]\n`;
    jest.spyOn(global, 'fetch').mockResolvedValue(responseOf(new TextEncoder().encode(body)));

    await expect(collectTokens(createProvider().stream(MESSAGES))).resolves.toEqual(['Cinq ', 'ans.']);
  });

  it('sends no token limit, so that the answer is never truncated', async () => {
    const fetchSpy = jest.spyOn(global, 'fetch').mockResolvedValue(responseOf(new TextEncoder().encode(sseLine('ok'))));

    await collectTokens(createProvider().stream(MESSAGES));

    const payload = JSON.parse(String(fetchSpy.mock.calls[0]?.[1]?.body));
    expect(payload).toEqual({ model: 'test-model', messages: MESSAGES, temperature: 0.7, stream: true });
  });

  it('reads only delta.content: other fields and null contents yield nothing', async () => {
    const ignoredChoices = [{ delta: { text: 'x' } }, { text: { content: 'y' } }, { delta: { content: null } }, { delta: { role: 'assistant' } }];
    const ignoredLines = ignoredChoices.map((choice) => `data: ${JSON.stringify({ choices: [choice] })}\n`).join('');
    jest.spyOn(global, 'fetch').mockResolvedValue(responseOf(new TextEncoder().encode(`${ignoredLines}${sseLine('ok')}`)));

    await expect(collectTokens(createProvider().stream(MESSAGES))).resolves.toEqual(['ok']);
  });

  it('rebuilds a line split across network chunks', async () => {
    const bytes = new TextEncoder().encode(sseLine('prescription'));
    const middle = Math.floor(bytes.length / 2);
    jest.spyOn(global, 'fetch').mockResolvedValue(responseOf(bytes.slice(0, middle), bytes.slice(middle)));

    await expect(collectTokens(createProvider().stream(MESSAGES))).resolves.toEqual(['prescription']);
  });

  it('keeps a multi-byte character split across network chunks intact', async () => {
    const bytes = new TextEncoder().encode(sseLine('délai'));
    // `é` tient sur deux octets (0xC3 0xA9) : coupure entre les deux
    const splitAt = bytes.indexOf(0xc3) + 1;
    jest.spyOn(global, 'fetch').mockResolvedValue(responseOf(bytes.slice(0, splitAt), bytes.slice(splitAt)));

    await expect(collectTokens(createProvider().stream(MESSAGES))).resolves.toEqual(['délai']);
  });

  it('fails with an llm RagError when the API answers an HTTP error', async () => {
    jest.spyOn(global, 'fetch').mockResolvedValue(
      new Response('upstream down', { status: HTTP_SERVER_ERROR, statusText: 'Internal Server Error' }),
    );

    await expect(collectTokens(createProvider().stream(MESSAGES))).rejects.toMatchObject({
      name: 'RagError',
      stage: 'llm',
      code: 'API_ERROR',
    });
  });

  it("follows the caller's abort signal and ends without an error", async () => {
    const abortController = new AbortController();
    jest.spyOn(global, 'fetch').mockImplementation(async (_url, init) => {
      const requestSignal = init?.signal;
      const body = new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(new TextEncoder().encode(sseLine('Cinq ')));
          // Comme un vrai fetch, le corps échoue une fois le signal levé
          requestSignal?.addEventListener('abort', () => controller.error(requestSignal.reason));
        },
      });
      return new Response(body);
    });

    const tokens: string[] = [];
    for await (const token of createProvider().stream(MESSAGES, abortController.signal)) {
      tokens.push(token);
      abortController.abort();
    }

    expect(tokens).toEqual(['Cinq ']);
  });
});
