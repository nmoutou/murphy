import request from 'supertest';
import app from '../../app';

jest.mock('../../services/searchService', () => ({ searchDocuments: jest.fn() }));
jest.mock('../../infra/clients', () => ({ getInfraClients: jest.fn() }));
// `pino-http` exige une vraie instance Pino
jest.mock('../../utils/logger', () => ({
  logger: jest.requireActual<typeof import('pino')>('pino').pino({ level: 'silent' }),
}));

const SEARCH_MAX_REQUESTS = 60;
const HTTP_BAD_REQUEST = 400;
const HTTP_TOO_MANY_REQUESTS = 429;

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
