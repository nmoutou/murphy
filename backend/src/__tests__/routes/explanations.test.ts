import type { AddressInfo } from 'net';
import type { LlmAnswer, LlmRequest } from '../../infra/llm';
import type { ExplainedDocument } from '../../types/explanation';
import http from 'http';
import request from 'supertest';
import app from '../../app';
import { getInfraClients } from '../../infra/clients';
import { RagError } from '../../types/rag';

jest.mock('../../infra/clients', () => {
  const clients = { mongo: { fetchExplainedDocuments: jest.fn() }, llm: { streamAnswer: jest.fn() } };
  return { getInfraClients: () => clients };
});
jest.mock('../../middleware/explanationRateLimiter', () => {
  const pass = (_req: unknown, _res: unknown, next: () => void) => next();
  return { explanationRateLimiter: pass, explanationQuotaLimiter: pass };
});
// `pino-http` exige une vraie instance Pino
jest.mock('../../utils/logger', () => ({
  logger: jest.requireActual<typeof import('pino')>('pino').pino({ level: 'silent' }),
}));

const PATH = '/api/v1/explanations';
const QUESTION = 'Que dit cet article ?';
const BODY = { selection: ['LEGIARTI1'], messages: [{ role: 'user', content: QUESTION }] };
const ARTICLE: ExplainedDocument = {
  identifier: 'LEGIARTI1',
  title: 'Article 2224',
  content: 'Cinq ans.',
  documentType: 'article',
  parentTextTitles: [],
  metadata: {},
};

const { mongo, llm } = getInfraClients();

const answerWith = (fragments: readonly string[], failAfter?: number) =>
  async function* ({ signal }: LlmRequest): LlmAnswer {
    for (const [index, fragment] of fragments.entries()) {
      if (index === failAfter) throw new RagError('generation', 'LLM_FAILED', 'LLM call failed: AI_APICallError, status 500');
      await new Promise((resolve) => setTimeout(resolve, 5));
      if (signal.aborted) return undefined;
      yield fragment;
    }
    return undefined;
  };

beforeEach(() => {
  jest.mocked(mongo.fetchExplainedDocuments).mockResolvedValue([ARTICLE]);
  jest.mocked(llm.streamAnswer).mockImplementation(answerWith(['Bon', 'jour']));
});

describe('POST /api/v1/explanations', () => {
  it('streams the answer as server-sent events', async () => {
    const response = await request(app).post(PATH).send(BODY);

    expect(response.status).toBe(200);
    expect(response.headers['content-type']).toContain('text/event-stream');
    expect(response.text).toContain('"type":"text-delta"');
    expect(response.text).toContain('"delta":"Bon"');
    expect(response.text).toContain('"delta":"jour"');
    expect(response.text).toContain('"type":"finish"');
  });

  it('refuses an invalid request with VALIDATION_ERROR, without calling the LLM', async () => {
    const response = await request(app).post(PATH).send({ ...BODY, selection: ['A', 'A'] });

    expect(response.status).toBe(400);
    expect(response.body.status.message).toBe('VALIDATION_ERROR');
    expect(llm.streamAnswer).not.toHaveBeenCalled();
  });

  it('answers 404 DOCUMENT_NOT_FOUND for a selection with an unknown document', async () => {
    jest.mocked(mongo.fetchExplainedDocuments).mockRejectedValue(new RagError('request', 'DOCUMENT_NOT_FOUND', 'No document'));

    const response = await request(app).post(PATH).send(BODY);

    expect(response.status).toBe(404);
    expect(response.body.status.message).toBe('DOCUMENT_NOT_FOUND');
  });

  it('counts a long segment against the budget instead of refusing its size first', async () => {
    const longQuestion = 'é'.repeat(100_001);

    const response = await request(app).post(PATH).send({ ...BODY, messages: [{ role: 'user', content: longQuestion }] });

    expect(response.status).toBe(400);
    expect(response.body.status.message).toBe('CONTEXT_TOO_LARGE');
  });

  it('counts a long segment whose accents arrive escaped as \\uXXXX', async () => {
    const escaped = JSON.stringify({ ...BODY, messages: [{ role: 'user', content: 'é'.repeat(100_001) }] }).replace(/é/g, '\\u00e9');

    const response = await request(app).post(PATH).set('Content-Type', 'application/json').send(escaped);

    expect(response.body.status.message).toBe('CONTEXT_TOO_LARGE');
  });

  it('answers 502 LLM_FAILED when the LLM fails before its first fragment', async () => {
    jest.mocked(llm.streamAnswer).mockImplementation(answerWith(['Bon'], 0));

    const response = await request(app).post(PATH).send(BODY);

    expect(response.status).toBe(502);
    expect(response.body.status.message).toBe('LLM_FAILED');
  });

  it('sends an error event carrying the code alone when the LLM fails mid-stream', async () => {
    jest.mocked(llm.streamAnswer).mockImplementation(answerWith(['Bon', 'jour'], 1));

    const response = await request(app).post(PATH).send(BODY);

    expect(response.status).toBe(200);
    expect(response.text).toContain('"delta":"Bon"');
    expect(response.text).toContain('{"type":"error","errorText":"LLM_FAILED"}');
    expect(response.text).not.toContain('status 500');
  });

  it('cuts the LLM call when the client leaves mid-stream', async () => {
    let signal: AbortSignal | undefined;
    jest.mocked(llm.streamAnswer).mockImplementation((llmRequest) => {
      signal = llmRequest.signal;
      return answerWith(Array(100).fill('mot '))(llmRequest);
    });
    const server = http.createServer(app).listen(0);
    const { port } = server.address() as AddressInfo;

    await new Promise<void>((resolve) => {
      const clientRequest = http.request({ port, path: PATH, method: 'POST', headers: { 'Content-Type': 'application/json' } }, (response) => {
        response.once('data', () => {
          clientRequest.destroy();
          resolve();
        });
      });
      clientRequest.on('error', () => undefined);
      clientRequest.end(JSON.stringify(BODY));
    });
    await new Promise((resolve) => setTimeout(resolve, 50));
    server.close();

    expect(signal?.aborted).toBe(true);
  });
});
