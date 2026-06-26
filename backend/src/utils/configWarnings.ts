import logger from './logger';

const CRITICAL_ENV = [
  'LLM_API_ENDPOINT',
  'LLM_API_KEY',
  'LLM_MODEL',
  'MONGODB_URI',
];

const OPTIONAL_ENV = [
  'LLM_TEMPERATURE',
  'LLM_MAX_TOKENS',
  'LLM_TIMEOUT',
  'MONGODB_DATABASE',
  'MONGODB_COLLECTION',
  'MONGODB_TIMEOUT',
  'EMBEDDING_SERVICE_URL',
  'EMBEDDING_SERVICE_TIMEOUT',
  'EMBEDDING_MODEL_NAME',
  'QDRANT_URL',
  'QDRANT_COLLECTION',
  'RETRIEVAL_MIN_SCORE',
  'RETRIEVAL_TOP_K',
  'SYSTEM_PROMPT',
  'CORS_ORIGIN',
  'PORT',
  'LOG_LEVEL',
  'RATE_LIMIT_WINDOW_MS',
  'RATE_LIMIT_MAX',
  'STREAM_RATE_LIMIT_WINDOW_MS',
  'STREAM_RATE_LIMIT_MAX',
];

export function checkEnvironment(): void {
  const missing = CRITICAL_ENV.filter((v) => !process.env[v]);
  const unset = OPTIONAL_ENV.filter((v) => !process.env[v]);

  if (missing.length > 0) {
    logger.error(`Critical env vars missing: ${missing.join(', ')}`);
  }
  if (unset.length > 0) {
    logger.warn(`Env vars using fallbacks: ${unset.join(', ')}`);
  }
  if (missing.length === 0) {
    logger.info('Environment configured');
  }
}
