import { loadConfig } from '../config';

const REQUIRED_ENV = {
  MONGODB_URI: 'mongodb://mongo:27017',
  OPENSEARCH_INDEX: 'documents',
  EMBEDDING_QUERY_INSTRUCTION: 'Instruct: Retrieve text based on user query.\nQuery:',
  LLM_BASE_URL: 'https://llm.test/v1',
  LLM_API_KEY: 'secret',
  LLM_MODEL: 'some-model',
};

describe('loadConfig', () => {
  it('falls back on the defaults when the environment is empty', () => {
    const { config } = loadConfig({});

    expect(config.server).toEqual({ port: 5000, nodeEnv: 'development', isProduction: false, logLevel: 'debug' });
    expect(config.http.corsOrigins).toBe(false);
    expect(config.http.rateLimit).toEqual({ windowMs: 900_000, limit: 600 });
    expect(config.http.searchRateLimit).toEqual({ windowMs: 60_000, limit: 60 });
    expect(config.mongo).toMatchObject({ database: 'MURPHY_DATA' });
    expect(config.opensearch).toEqual({ url: 'http://opensearch:9200', index: '', timeoutMs: 10_000 });
    expect(config.pagination).toEqual({ sizes: [10, 25, 50], depth: 100 });
  });

  it('reads the variables that are set', () => {
    const { config } = loadConfig({
      ...REQUIRED_ENV,
      NODE_ENV: 'production',
      CORS_ORIGIN: 'http://a.test,http://b.test',
      PAGINATION_SIZES: '20, 40',
      PAGINATION_DEPTH: '200',
      OPENSEARCH_TIMEOUT: '2500',
    });

    expect(config.server).toMatchObject({ isProduction: true, logLevel: 'info' });
    expect(config.http.corsOrigins).toEqual(['http://a.test', 'http://b.test']);
    expect(config.pagination).toEqual({ sizes: [20, 40], depth: 200 });
    expect(config.opensearch).toMatchObject({ index: 'documents', timeoutMs: 2500 });
  });

  it('reads the log level from NODE_LOG_LEVEL', () => {
    const { config } = loadConfig({ NODE_LOG_LEVEL: 'warn' });

    expect(config.server.logLevel).toBe('warn');
  });

  it('treats an empty value as unset, as Compose passes one for a missing variable', () => {
    const { config, report } = loadConfig({ PAGINATION_SIZES: '', OPENSEARCH_INDEX: '' });

    expect(config.pagination.sizes).toEqual([10, 25, 50]);
    expect(report.defaulted).toContain('PAGINATION_SIZES');
    expect(report.missingRequired).toContain('OPENSEARCH_INDEX');
  });

  it.each([
    ['PAGINATION_SIZES', '10,2.5', 'PAGINATION_SIZES must be an integer, got "2.5"'],
    ['PAGINATION_SIZES', '10,,25', 'PAGINATION_SIZES must be an integer, got ""'],
    ['PORT', '50OO', 'PORT must be an integer, got "50OO"'],
    ['OPENSEARCH_TIMEOUT', '10s', 'OPENSEARCH_TIMEOUT must be an integer, got "10s"'],
  ])('refuses %s=%s, naming the variable', (name, value, message) => {
    expect(() => loadConfig({ [name]: value })).toThrow(message);
  });

  it.each([
    ['a zero size', '10,0', '100', 'must be between 1 and PAGINATION_DEPTH (100), got 0'],
    ['a size above the depth', '10,25', '20', 'must be between 1 and PAGINATION_DEPTH (20), got 25'],
    ['a repeated size', '10,25,10', '100', 'PAGINATION_SIZES must not repeat a size, got 10,25,10'],
    ['a negative depth', '10', '-1', 'PAGINATION_DEPTH must be positive, got -1'],
    ['a depth above the k-NN limit', '10', '10001', 'PAGINATION_DEPTH (10001) must not exceed 10000'],
  ])('refuses %s', (_case, sizes, depth, message) => {
    expect(() => loadConfig({ PAGINATION_SIZES: sizes, PAGINATION_DEPTH: depth })).toThrow(message);
  });

  it('accepts a size equal to the depth, a size that does not divide it, and the k-NN limit itself', () => {
    expect(loadConfig({ PAGINATION_SIZES: '10', PAGINATION_DEPTH: '10' }).config.pagination.depth).toBe(10);
    expect(loadConfig({ PAGINATION_SIZES: '30' }).config.pagination.sizes).toEqual([30]);
    expect(loadConfig({ PAGINATION_DEPTH: '10000' }).config.pagination.depth).toBe(10_000);
  });

  it('reports the missing required variables and the defaulted optional ones', () => {
    const { report } = loadConfig({ ...REQUIRED_ENV, OPENSEARCH_INDEX: undefined });

    expect(report.missingRequired).toEqual(['OPENSEARCH_INDEX']);
    expect(report.defaulted).toContain('MONGODB_DATABASE');
    expect(report.defaulted).not.toContain('MONGODB_URI');
  });

  it('reads the query instruction as is, line break included', () => {
    const { config } = loadConfig(REQUIRED_ENV);

    expect(config.embedding.queryInstruction).toBe('Instruct: Retrieve text based on user query.\nQuery:');
  });

  it('reports a missing query instruction as a missing required variable', () => {
    const { report } = loadConfig({ ...REQUIRED_ENV, EMBEDDING_QUERY_INSTRUCTION: undefined });

    expect(report.missingRequired).toEqual(['EMBEDDING_QUERY_INSTRUCTION']);
  });

  it('reads the LLM and the explanation limits, with their defaults', () => {
    const { config } = loadConfig(REQUIRED_ENV);

    expect(config.llm).toEqual({
      baseUrl: 'https://llm.test/v1',
      apiKey: 'secret',
      model: 'some-model',
      timeoutMs: 30_000,
      contextMaxChars: 100_000,
      maxOutputTokens: 2_000,
    });
    expect(config.http.explanationRateLimit).toEqual({ windowMs: 60_000, limit: 10 });
    expect(config.http.explanationDailyLimit).toBe(200);
  });

  it('reports each missing LLM variable as required', () => {
    const { report } = loadConfig({ ...REQUIRED_ENV, LLM_BASE_URL: '', LLM_API_KEY: undefined, LLM_MODEL: undefined });

    expect(report.missingRequired).toEqual(['LLM_BASE_URL', 'LLM_API_KEY', 'LLM_MODEL']);
  });

  it.each(['LLM_TIMEOUT', 'LLM_CONTEXT_MAX_CHARS', 'LLM_MAX_OUTPUT_TOKENS'])('refuses a %s that is not positive', (name) => {
    expect(() => loadConfig({ ...REQUIRED_ENV, [name]: '0' })).toThrow(`${name} must be positive, got 0`);
  });
});
