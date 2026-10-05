import { loadConfig } from '../config';

const REQUIRED_ENV = {
  MONGODB_URI: 'mongodb://mongo:27017',
  OPENSEARCH_INDEX: 'documents',
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
    expect(config.opensearch).toEqual({ url: 'http://opensearch:9200', index: '', timeoutMs: 10_000 });
    expect(config.pagination).toEqual({ size: 10, depth: 100 });
    expect(config.llm.systemPrompt).toContain('assistant juridique');
  });

  it('reads the variables that are set', () => {
    const { config } = loadConfig({
      ...REQUIRED_ENV,
      NODE_ENV: 'production',
      CORS_ORIGIN: 'http://a.test,http://b.test',
      PAGINATION_SIZE: '20',
      PAGINATION_DEPTH: '200',
      OPENSEARCH_TIMEOUT: '2500',
      LLM_TEMPERATURE: '0.2',
      SYSTEM_PROMPT: 'Consigne de test',
    });

    expect(config.server).toMatchObject({ isProduction: true, logLevel: 'info' });
    expect(config.http.corsOrigins).toEqual(['http://a.test', 'http://b.test']);
    expect(config.pagination).toEqual({ size: 20, depth: 200 });
    expect(config.opensearch).toMatchObject({ index: 'documents', timeoutMs: 2500 });
    expect(config.llm).toMatchObject({ apiKey: 'test-key', temperature: 0.2, systemPrompt: 'Consigne de test' });
  });

  it('reads the log level from NODE_LOG_LEVEL', () => {
    const { config } = loadConfig({ NODE_LOG_LEVEL: 'warn' });

    expect(config.server.logLevel).toBe('warn');
  });

  it('treats an empty value as unset, as Compose passes one for a missing variable', () => {
    const { config, report } = loadConfig({ PAGINATION_SIZE: '', LLM_API_KEY: '' });

    expect(config.pagination.size).toBe(10);
    expect(report.defaulted).toContain('PAGINATION_SIZE');
    expect(report.missingRequired).toContain('LLM_API_KEY');
  });

  it.each([
    ['LLM_TEMPERATURE', 'chaud', 'LLM_TEMPERATURE must be a number, got "chaud"'],
    ['PAGINATION_SIZE', '2.5', 'PAGINATION_SIZE must be an integer, got "2.5"'],
    ['PORT', '50OO', 'PORT must be an integer, got "50OO"'],
    ['OPENSEARCH_TIMEOUT', '10s', 'OPENSEARCH_TIMEOUT must be an integer, got "10s"'],
  ])('refuses %s=%s, naming the variable', (name, value, message) => {
    expect(() => loadConfig({ [name]: value })).toThrow(message);
  });

  it.each([
    ['a zero size', '0', '100', 'must be positive'],
    ['a negative depth', '10', '-1', 'must be positive'],
    ['a depth below the size', '10', '5', 'PAGINATION_DEPTH (5) must be at least PAGINATION_SIZE (10)'],
    ['a depth above the k-NN limit', '10', '10001', 'PAGINATION_DEPTH (10001) must not exceed 10000'],
  ])('refuses %s', (_case, size, depth, message) => {
    expect(() => loadConfig({ PAGINATION_SIZE: size, PAGINATION_DEPTH: depth })).toThrow(message);
  });

  it('accepts a depth equal to the size, and the k-NN limit itself', () => {
    expect(loadConfig({ PAGINATION_SIZE: '10', PAGINATION_DEPTH: '10' }).config.pagination.depth).toBe(10);
    expect(loadConfig({ PAGINATION_DEPTH: '10000' }).config.pagination.depth).toBe(10_000);
  });

  it('reports the missing required variables and the defaulted optional ones', () => {
    const { report } = loadConfig({ ...REQUIRED_ENV, LLM_API_KEY: undefined });

    expect(report.missingRequired).toEqual(['LLM_API_KEY']);
    expect(report.defaulted).toContain('MONGODB_DATABASE');
    expect(report.defaulted).not.toContain('MONGODB_URI');
  });
});
