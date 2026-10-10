import request from 'supertest';
import app from '../../app';
import { consumeSearchQuota } from '../../middleware/searchRateLimiter';

jest.mock('../../services/searchService', () => ({ searchDocuments: jest.fn() }));
jest.mock('../../infra/clients', () => ({ getInfraClients: jest.fn() }));
// `pino-http` exige une vraie instance Pino
jest.mock('../../utils/logger', () => ({
  logger: jest.requireActual<typeof import('pino')>('pino').pino({ level: 'silent' }),
}));

const SEARCH_MAX_REQUESTS = 60;
const HTTP_BAD_REQUEST = 400;
const HTTP_TOO_MANY_REQUESTS = 429;

const consumeRepeatedly = async (remoteAddress: string, times: number): Promise<boolean[]> => {
  const verdicts: boolean[] = [];
  for (let attempt = 0; attempt < times; attempt++) verdicts.push(await consumeSearchQuota(remoteAddress));
  return verdicts;
};

describe('consumeSearchQuota', () => {
  it('grants the budget, then refuses', async () => {
    const verdicts = await consumeRepeatedly('198.51.100.1', SEARCH_MAX_REQUESTS + 1);

    expect(verdicts.slice(0, SEARCH_MAX_REQUESTS).every(Boolean)).toBe(true);
    expect(verdicts[SEARCH_MAX_REQUESTS]).toBe(false);
  });

  it('counts each address separately', async () => {
    await consumeRepeatedly('198.51.100.2', SEARCH_MAX_REQUESTS + 1);

    await expect(consumeSearchQuota('198.51.100.3')).resolves.toBe(true);
  });

  it('refuses a client without an address', async () => {
    await expect(consumeSearchQuota(undefined)).resolves.toBe(false);
  });
});

describe('POST /api/v1/search rate limit', () => {
  it('is not dodged by forging a new X-Forwarded-For on each request', async () => {
    // express-rate-limit signale l'en-tête qu'il ignore : c'est le symptôme d'un
    // `trust proxy` manquant derrière un proxy
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => undefined);
    const statuses: number[] = [];
    for (let attempt = 0; attempt <= SEARCH_MAX_REQUESTS; attempt++) {
      const response = await request(app)
        .post('/api/v1/search')
        .set('X-Forwarded-For', `203.0.113.${attempt}`)
        .send({});
      statuses.push(response.status);
    }

    expect(statuses.slice(0, SEARCH_MAX_REQUESTS)).toEqual(Array(SEARCH_MAX_REQUESTS).fill(HTTP_BAD_REQUEST));
    expect(statuses[SEARCH_MAX_REQUESTS]).toBe(HTTP_TOO_MANY_REQUESTS);
    expect(consoleError).toHaveBeenCalledWith(expect.objectContaining({ code: 'ERR_ERL_UNEXPECTED_X_FORWARDED_FOR' }));
  });

  it('answers SEARCH_RATE_LIMIT_EXCEEDED once the budget is spent', async () => {
    const response = await request(app).post('/api/v1/search').send({});

    expect(response.status).toBe(HTTP_TOO_MANY_REQUESTS);
    expect(response.body.status.message).toBe('SEARCH_RATE_LIMIT_EXCEEDED');
  });
});
