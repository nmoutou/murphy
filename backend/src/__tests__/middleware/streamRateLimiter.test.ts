import request from 'supertest';
import app from '../../app';
import { consumeStreamQuota } from '../../middleware/streamRateLimiter';

jest.mock('../../services/chatService', () => ({ createChatStream: jest.fn() }));
jest.mock('../../infra/clients', () => ({ getInfraClients: jest.fn() }));
// `pino-http` exige une vraie instance Pino
jest.mock('../../utils/logger', () => ({
  logger: jest.requireActual<typeof import('pino')>('pino').pino({ level: 'silent' }),
}));

const STREAM_MAX_REQUESTS = 10;
const HTTP_BAD_REQUEST = 400;
const HTTP_TOO_MANY_REQUESTS = 429;

const consumeRepeatedly = async (remoteAddress: string, times: number): Promise<boolean[]> => {
  const verdicts: boolean[] = [];
  for (let attempt = 0; attempt < times; attempt++) verdicts.push(await consumeStreamQuota(remoteAddress));
  return verdicts;
};

describe('consumeStreamQuota', () => {
  it('grants the budget, then refuses', async () => {
    const verdicts = await consumeRepeatedly('198.51.100.1', STREAM_MAX_REQUESTS + 1);

    expect(verdicts.slice(0, STREAM_MAX_REQUESTS).every(Boolean)).toBe(true);
    expect(verdicts[STREAM_MAX_REQUESTS]).toBe(false);
  });

  it('counts each address separately', async () => {
    await consumeRepeatedly('198.51.100.2', STREAM_MAX_REQUESTS + 1);

    await expect(consumeStreamQuota('198.51.100.3')).resolves.toBe(true);
  });

  it('refuses a client without an address', async () => {
    await expect(consumeStreamQuota(undefined)).resolves.toBe(false);
  });
});

describe('POST /api/v1/chat/streams rate limit', () => {
  it('is not dodged by forging a new X-Forwarded-For on each request', async () => {
    // express-rate-limit signale l'en-tête qu'il ignore : c'est le symptôme d'un
    // `trust proxy` manquant derrière un proxy
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => undefined);
    const statuses: number[] = [];
    for (let attempt = 0; attempt <= STREAM_MAX_REQUESTS; attempt++) {
      const response = await request(app)
        .post('/api/v1/chat/streams')
        .set('X-Forwarded-For', `203.0.113.${attempt}`)
        .send({ messages: [] });
      statuses.push(response.status);
    }

    expect(statuses.slice(0, STREAM_MAX_REQUESTS)).toEqual(Array(STREAM_MAX_REQUESTS).fill(HTTP_BAD_REQUEST));
    expect(statuses[STREAM_MAX_REQUESTS]).toBe(HTTP_TOO_MANY_REQUESTS);
    expect(consoleError).toHaveBeenCalledWith(expect.objectContaining({ code: 'ERR_ERL_UNEXPECTED_X_FORWARDED_FOR' }));
  });
});

describe('POST /api/v1/chat/completions rate limit', () => {
  it('draws from the budget of /streams', async () => {
    // Épuise ce que les tests précédents ont laissé du budget de loopback
    let streamsStatus = HTTP_BAD_REQUEST;
    for (let attempt = 0; attempt <= STREAM_MAX_REQUESTS && streamsStatus !== HTTP_TOO_MANY_REQUESTS; attempt++) {
      streamsStatus = (await request(app).post('/api/v1/chat/streams').send({ messages: [] })).status;
    }

    const response = await request(app).post('/api/v1/chat/completions').send({ messages: [] });

    expect(streamsStatus).toBe(HTTP_TOO_MANY_REQUESTS);
    expect(response.status).toBe(HTTP_TOO_MANY_REQUESTS);
    expect(response.body.status.message).toBe('STREAM_RATE_LIMIT_EXCEEDED');
  });
});
