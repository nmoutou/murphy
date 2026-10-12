import type { LlmAnswer, LlmRequest } from '../../infra/llm';
import type { ExplainedDocument } from '../../types/explanation';
import { openAnswer, prepareExplanation } from '../../services/explanationService';
import { getInfraClients } from '../../infra/clients';
import { RagError } from '../../types/rag';

const BUDGET = 6_000;
const TIMEOUT_MS = 50;

jest.mock('../../config', () => ({ config: { llm: { timeoutMs: 50, contextMaxChars: 6_000 } } }));
jest.mock('../../infra/clients', () => {
  const clients = { mongo: { fetchExplainedDocuments: jest.fn() }, llm: { streamAnswer: jest.fn() } };
  return { getInfraClients: () => clients };
});
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

const ARTICLE: ExplainedDocument = {
  identifier: 'LEGIARTI1',
  title: 'Article 2224',
  content: 'Les actions personnelles se prescrivent par cinq ans.',
  documentType: 'article',
  parentTextTitles: [],
  metadata: { statut: 'VIGUEUR' },
};
const REQUEST = { selection: ['LEGIARTI1'], messages: [{ role: 'user' as const, content: 'Résume.' }] };

const { mongo, llm } = getInfraClients();

const answerWith = (fragments: readonly string[], delayMs = 0) =>
  async function* (request: LlmRequest): LlmAnswer {
    for (const fragment of fragments) {
      await new Promise((resolve) => setTimeout(resolve, delayMs));
      if (request.signal.aborted) return undefined;
      yield fragment;
    }
    return { inputTokens: 10, outputTokens: 2 };
  };

const PREPARED = { instructions: 'Explique.', messages: REQUEST.messages, documentCount: 1, contextLength: 20 };

beforeEach(() => {
  jest.mocked(mongo.fetchExplainedDocuments).mockResolvedValue([ARTICLE]);
});

describe('prepareExplanation', () => {
  it('builds the instructions from the prompt and the documents read in Mongo', async () => {
    const prepared = await prepareExplanation(REQUEST);

    expect(mongo.fetchExplainedDocuments).toHaveBeenCalledWith(['LEGIARTI1'], expect.arrayContaining(['statut']));
    expect(prepared.instructions).toContain('Tu ne qualifies aucune situation');
    expect(prepared.instructions).toContain('[1] Article 2224');
    expect(prepared.instructions).toContain('Statut de vigueur : VIGUEUR');
    expect(prepared).toMatchObject({ documentCount: 1, messages: REQUEST.messages });
    expect(prepared.contextLength).toBe([...prepared.instructions].length + 'Résume.'.length);
  });

  it('refuses a context above the budget, segment included', async () => {
    const longQuestion = 'a'.repeat(BUDGET);

    await expect(prepareExplanation({ ...REQUEST, messages: [{ role: 'user', content: longQuestion }] }))
      .rejects.toMatchObject({ stage: 'request', code: 'CONTEXT_TOO_LARGE' });
  });

  it('merges consecutive questions before sending them', async () => {
    const messages = [{ role: 'user' as const, content: 'Une' }, { role: 'user' as const, content: 'Deux' }];

    const prepared = await prepareExplanation({ ...REQUEST, messages });

    expect(prepared.messages).toEqual([{ role: 'user', content: 'Une\n\nDeux' }]);
  });
});

describe('openAnswer', () => {
  it('waits for the first fragment, then hands over the rest', async () => {
    jest.mocked(llm.streamAnswer).mockImplementation(answerWith(['Bon', 'jour']));

    const { first, rest } = await openAnswer(PREPARED, new AbortController().signal);

    expect(first).toEqual({ done: false, value: 'Bon' });
    await expect(rest.next()).resolves.toEqual({ done: false, value: 'jour' });
    expect(llm.streamAnswer).toHaveBeenCalledWith(expect.objectContaining({ instructions: 'Explique.', messages: REQUEST.messages }));
  });

  it('fails with TIMEOUT when no fragment comes in time, and cuts the call', async () => {
    let signal: AbortSignal | undefined;
    jest.mocked(llm.streamAnswer).mockImplementation((request) => {
      signal = request.signal;
      return answerWith(['trop tard'], TIMEOUT_MS * 4)(request);
    });

    await expect(openAnswer(PREPARED, new AbortController().signal)).rejects.toMatchObject({ stage: 'generation', code: 'TIMEOUT' });
    expect(signal?.aborted).toBe(true);
  });

  it('lets an error before the first fragment through, before any stream', async () => {
    const failure = new RagError('generation', 'LLM_FAILED', 'LLM call failed: AI_APICallError, status 401');
    jest.mocked(llm.streamAnswer).mockImplementation(async function* (): LlmAnswer {
      yield* [];
      throw failure;
    });

    await expect(openAnswer(PREPARED, new AbortController().signal)).rejects.toMatchObject({ code: 'LLM_FAILED' });
  });

  it('passes the departure of the client on to the LLM', async () => {
    let signal: AbortSignal | undefined;
    jest.mocked(llm.streamAnswer).mockImplementation((request) => {
      signal = request.signal;
      return answerWith(['a', 'b'])(request);
    });
    const client = new AbortController();

    await openAnswer(PREPARED, client.signal);
    client.abort();

    expect(signal?.aborted).toBe(true);
  });
});
