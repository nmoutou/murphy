import express, { Express } from 'express';
import request from 'supertest';
import healthRouter from '../../routes/health';

const mockPing = jest.fn();

jest.mock('../../infra/clients', () => ({
  getInfraClients: () => ({ mongo: { getDb: () => ({ admin: () => ({ ping: mockPing }) }) } }),
}));
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

const HTTP_OK = 200;
const HTTP_UNAUTHORIZED = 401;
const HTTP_SERVER_ERROR = 500;
const HTTP_SERVICE_UNAVAILABLE = 503;

interface HttpStatuses {
  readonly tei: number;
  readonly opensearch: number;
  readonly llm?: number;
}

/** Répond aux sondes TEI (`/health`), OpenSearch (`/_cluster/health`) et LLM (`/models`) */
const mockHttpServices = ({ tei, opensearch, llm = HTTP_OK }: HttpStatuses): void => {
  jest.spyOn(global, 'fetch').mockImplementation(async (url) => {
    const target = String(url);
    if (target.endsWith('/_cluster/health')) return new Response(null, { status: opensearch });
    if (target.endsWith('/models')) return new Response(null, { status: llm });
    return new Response(null, { status: tei });
  });
};

let app: Express;

beforeEach(() => {
  app = express();
  app.use('/api/v1/health', healthRouter);
  mockPing.mockResolvedValue({ ok: 1 });
});

describe('GET /api/v1/health', () => {
  it('reports ok with the latency of each service when all are up', async () => {
    mockHttpServices({ tei: HTTP_OK, opensearch: HTTP_OK });

    const response = await request(app).get('/api/v1/health');

    expect(response.status).toBe(HTTP_OK);
    expect(response.body.data.status).toBe('ok');
    for (const service of ['tei', 'opensearch', 'mongodb', 'llm']) {
      expect(response.body.data.services[service]).toEqual({ status: 'ok', latencyMs: expect.any(Number) });
    }
  });

  it('reports degraded with a 503 when one service is down', async () => {
    mockHttpServices({ tei: HTTP_SERVER_ERROR, opensearch: HTTP_OK });

    const response = await request(app).get('/api/v1/health');

    expect(response.status).toBe(HTTP_SERVICE_UNAVAILABLE);
    expect(response.body.status.message).toBe('UPSTREAM_UNAVAILABLE');
    expect(response.body.data.status).toBe('degraded');
    expect(response.body.data.services.tei).toMatchObject({ status: 'down', message: 'HTTP 500' });
  });

  it('reports degraded when the LLM alone is down, probing it with its key', async () => {
    mockHttpServices({ tei: HTTP_OK, opensearch: HTTP_OK, llm: HTTP_UNAUTHORIZED });

    const response = await request(app).get('/api/v1/health');

    expect(response.status).toBe(HTTP_SERVICE_UNAVAILABLE);
    expect(response.body.data.status).toBe('degraded');
    expect(response.body.data.services.llm).toMatchObject({ status: 'down', message: 'HTTP 401' });
    const llmCall = jest.mocked(fetch).mock.calls.find(([url]) => String(url).endsWith('/models'));
    expect(llmCall?.[1]?.headers).toEqual({ Authorization: expect.stringMatching(/^Bearer /) });
  });

  it('reports down when two services are down', async () => {
    jest.spyOn(global, 'fetch').mockRejectedValue(new Error('connect ECONNREFUSED'));
    mockPing.mockRejectedValue(new Error('MongoDB unreachable'));

    const response = await request(app).get('/api/v1/health');

    expect(response.status).toBe(HTTP_SERVICE_UNAVAILABLE);
    expect(response.body.data.status).toBe('down');
    expect(response.body.data.services.mongodb).toMatchObject({ status: 'down', message: 'MongoDB unreachable' });
  });
});

describe('GET /api/v1/health/services', () => {
  it('answers like /', async () => {
    mockHttpServices({ tei: HTTP_OK, opensearch: HTTP_OK });

    const response = await request(app).get('/api/v1/health/services');

    expect(response.status).toBe(HTTP_OK);
    expect(Object.keys(response.body.data.services)).toEqual(['tei', 'opensearch', 'mongodb', 'llm']);
  });
});
