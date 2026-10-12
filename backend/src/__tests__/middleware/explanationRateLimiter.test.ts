import express, { Express, Request, Response } from 'express';
import request from 'supertest';
import { explanationQuotaLimiter, explanationRateLimiter } from '../../middleware/explanationRateLimiter';

jest.mock('../../config', () => ({
  config: { http: { explanationRateLimit: { windowMs: 60_000, limit: 3 }, explanationDailyLimit: 2 } },
}));
jest.mock('../../utils/logger', () => ({ logger: { warn: jest.fn() } }));

const HTTP_OK = 200;
const HTTP_BAD_REQUEST = 400;
const HTTP_TOO_MANY_REQUESTS = 429;

/** `{ fail: true }` : une requête refusée avant tout appel au LLM */
const answer = (req: Request, res: Response) => {
  res.status(req.body.fail ? HTTP_BAD_REQUEST : HTTP_OK).end();
};

const appWith = (limiter: express.RequestHandler): Express => {
  const app = express();
  app.use(express.json());
  app.post('/', limiter, answer);
  return app;
};

describe('explanationRateLimiter', () => {
  it('answers EXPLANATION_RATE_LIMIT_EXCEEDED past the per-IP budget', async () => {
    const app = appWith(explanationRateLimiter);
    for (let attempt = 0; attempt < 3; attempt++) await request(app).post('/').send({});

    const response = await request(app).post('/').send({});

    expect(response.status).toBe(HTTP_TOO_MANY_REQUESTS);
    expect(response.body.status.message).toBe('EXPLANATION_RATE_LIMIT_EXCEEDED');
  });
});

describe('explanationQuotaLimiter', () => {
  it('counts the calls under one key, refused requests aside', async () => {
    const app = appWith(explanationQuotaLimiter);

    const statuses = [];
    for (const body of [{ fail: true }, {}, { fail: true }, {}, {}]) {
      statuses.push((await request(app).post('/').send(body)).status);
    }

    expect(statuses).toEqual([HTTP_BAD_REQUEST, HTTP_OK, HTTP_BAD_REQUEST, HTTP_OK, HTTP_TOO_MANY_REQUESTS]);
  });

  it('answers EXPLANATION_QUOTA_EXCEEDED once the daily budget is spent', async () => {
    const response = await request(appWith(explanationQuotaLimiter)).post('/').send({});

    expect(response.body.status.message).toBe('EXPLANATION_QUOTA_EXCEEDED');
  });
});
