import { loadConfig } from '../config';

const REQUIRED_ENV = {
  MONGODB_URI: 'mongodb://mongo:27017',
  QDRANT_COLLECTION: 'chunks',
  LLM_API_ENDPOINT: 'http://llm.test/v1/chat/completions',
  LLM_API_KEY: 'test-key',
  LLM_MODEL: 'test-model',
};

describe('loadConfig', () => {
  it('falls back on the defaults when the environment is empty', () => {
    const { config } = loadConfig({});

    expect(config.server).toEqual({ port: 5000, nodeEnv: 'development', isProduction: false, logLevel: 'debug' });
    expect(config.http.corsOrigins).toBe(false);
    expect(config.http.streamRateLimit).toEqual({ windowMs: 60_000, limit: 10 });
    expect(config.mongo).toMatchObject({ database: 'MURPHY_DATA' });
    expect(config.qdrant).toEqual({ url: 'http://qdrant:6333', collection: '', timeoutMs: 10_000 });
    expect(config.retrieval).toEqual({ topK: 5, minScore: 0.5 });
    expect(config.llm.systemPrompt).toContain('assistant juridique');
  });

  it('reads the variables that are set', () => {
    const { config } = loadConfig({
      ...REQUIRED_ENV,
      NODE_ENV: 'production',
      CORS_ORIGIN: 'http://a.test,http://b.test',
      RETRIEVAL_TOP_K: '8',
      QDRANT_TIMEOUT: '2500',
      LLM_TEMPERATURE: '0.2',
      SYSTEM_PROMPT: 'Consigne de test',
    });

    expect(config.server).toMatchObject({ isProduction: true, logLevel: 'info' });
    expect(config.http.corsOrigins).toEqual(['http://a.test', 'http://b.test']);
    expect(config.retrieval.topK).toBe(8);
    expect(config.qdrant).toMatchObject({ collection: 'chunks', timeoutMs: 2500 });
    expect(config.llm).toMatchObject({ apiKey: 'test-key', temperature: 0.2, systemPrompt: 'Consigne de test' });
  });

  it('reads the log level from NODE_LOG_LEVEL', () => {
    const { config } = loadConfig({ NODE_LOG_LEVEL: 'warn' });

    expect(config.server.logLevel).toBe('warn');
  });

  it('treats an empty value as unset, as Compose passes one for a missing variable', () => {
    const { config, report } = loadConfig({ RETRIEVAL_TOP_K: '', LLM_API_KEY: '' });

    expect(config.retrieval.topK).toBe(5);
    expect(report.defaulted).toContain('RETRIEVAL_TOP_K');
    expect(report.missingRequired).toContain('LLM_API_KEY');
  });

  it.each([
    ['LLM_TEMPERATURE', 'chaud', 'LLM_TEMPERATURE must be a number, got "chaud"'],
    ['RETRIEVAL_TOP_K', '2.5', 'RETRIEVAL_TOP_K must be an integer, got "2.5"'],
    ['PORT', '50OO', 'PORT must be an integer, got "50OO"'],
    ['QDRANT_TIMEOUT', '10s', 'QDRANT_TIMEOUT must be an integer, got "10s"'],
  ])('refuses %s=%s, naming the variable', (name, value, message) => {
    expect(() => loadConfig({ [name]: value })).toThrow(message);
  });

  it('reports the missing required variables and the defaulted optional ones', () => {
    const { report } = loadConfig({ ...REQUIRED_ENV, LLM_API_KEY: undefined });

    expect(report.missingRequired).toEqual(['LLM_API_KEY']);
    expect(report.defaulted).toContain('MONGODB_DATABASE');
    expect(report.defaulted).not.toContain('MONGODB_URI');
  });
});
