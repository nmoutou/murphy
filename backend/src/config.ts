/**
 * Runtime Configuration
 * Reads and validates the environment once, at boot: every other module reads
 * `config`, never `process.env`. The reader records which variables were missing
 * or fell back to their default, so `checkEnvironment` reports from what was
 * actually read instead of a hand-kept list.
 *
 * No internal import here: `utils/logger.ts` depends on this module.
 */

type Environment = Readonly<Record<string, string | undefined>>;

export interface ServerConfig {
  readonly port: number;
  readonly nodeEnv: string;
  readonly isProduction: boolean;
  readonly logLevel: string;
}

export interface RateLimitConfig {
  readonly windowMs: number;
  readonly limit: number;
}

export interface HttpConfig {
  readonly corsOrigins: readonly string[] | false;
  readonly rateLimit: RateLimitConfig;
  readonly streamRateLimit: RateLimitConfig;
}

export interface MongoConfig {
  readonly uri: string;
  readonly database: string;
  readonly collection: string;
  readonly metaDatabase: string;
  readonly timeoutMs: number;
}

export interface QdrantConfig {
  readonly url: string;
  /** Used only when no ingestion run has published a collection (`infra/collectionPointer.ts`) */
  readonly fallbackCollection: string;
}

export interface EmbeddingConfig {
  readonly serviceUrl: string;
  readonly modelName: string;
  readonly timeoutMs: number;
}

export interface LlmConfig {
  readonly apiUrl: string;
  readonly apiKey: string;
  readonly model: string;
  readonly temperature: number;
  readonly maxTokens: number;
  readonly timeoutMs: number;
  readonly systemPrompt: string;
}

export interface RetrievalConfig {
  readonly topK: number;
  readonly minScore: number;
}

export interface AppConfig {
  readonly server: ServerConfig;
  readonly http: HttpConfig;
  readonly mongo: MongoConfig;
  readonly qdrant: QdrantConfig;
  readonly embedding: EmbeddingConfig;
  readonly llm: LlmConfig;
  readonly retrieval: RetrievalConfig;
}

export interface EnvironmentReport {
  /** Required variables left unset: the matching feature cannot work */
  readonly missingRequired: readonly string[];
  /** Optional variables left unset: their default applies */
  readonly defaulted: readonly string[];
}

export interface LoadedConfig {
  readonly config: AppConfig;
  readonly report: EnvironmentReport;
}

const DEFAULT_PORT = 5000;
const DEFAULT_NODE_ENV = 'development';
const PRODUCTION_NODE_ENV = 'production';
const DEFAULT_DEVELOPMENT_LOG_LEVEL = 'debug';
const DEFAULT_PRODUCTION_LOG_LEVEL = 'info';
const CORS_ORIGIN_SEPARATOR = ',';
const DEFAULT_RATE_LIMIT_WINDOW_MS = 900_000;
const DEFAULT_RATE_LIMIT_MAX = 100;
const DEFAULT_STREAM_RATE_LIMIT_WINDOW_MS = 60_000;
const DEFAULT_STREAM_RATE_LIMIT_MAX = 10;
/** Same name on both sides: the Mongo chunk collection and the Qdrant fallback */
const DEFAULT_CHUNK_COLLECTION = 'chunks';
const DEFAULT_MONGODB_DATABASE = 'LEGIFRANCE';
const DEFAULT_MONGODB_META_DATABASE = 'MURPHY_META';
const DEFAULT_MONGODB_TIMEOUT_MS = 10_000;
const DEFAULT_QDRANT_URL = 'http://qdrant:6333';
const DEFAULT_EMBEDDING_SERVICE_URL = 'http://embedding-service:80';
const DEFAULT_EMBEDDING_MODEL_NAME = 'all-mpnet-base-v2';
const DEFAULT_EMBEDDING_TIMEOUT_MS = 10_000;
const DEFAULT_LLM_TEMPERATURE = 0.7;
const DEFAULT_LLM_MAX_TOKENS = 1000;
const DEFAULT_LLM_TIMEOUT_MS = 30_000;
const DEFAULT_RETRIEVAL_TOP_K = 5;
const DEFAULT_RETRIEVAL_MIN_SCORE = 0.5;
const DEFAULT_SYSTEM_PROMPT =
  'Vous êtes un assistant juridique intelligent spécialisé dans le droit français. ' +
  "Répondez aux questions de l'utilisateur en vous basant sur les documents juridiques fournis. " +
  'Soyez précis, professionnel et citez les sources pertinentes. ' +
  'Si la réponse ne se trouve pas dans les documents fournis, dites-le clairement.';

interface EnvReader {
  /** Unset → `undefined`, recorded as defaulted */
  readonly optional: (name: string) => string | undefined;
  /** Unset → `''`, recorded as missing */
  readonly required: (name: string) => string;
  /** @throws Error when set to something that is not an integer */
  readonly integer: (name: string, fallback: number) => number;
  /** @throws Error when set to something that is not a finite number */
  readonly number: (name: string, fallback: number) => number;
  readonly report: () => EnvironmentReport;
}

const createEnvReader = (env: Environment): EnvReader => {
  const missingRequired: string[] = [];
  const defaulted: string[] = [];

  // Compose passes `VAR=` when the variable is absent from `.env.dev`: empty means unset
  const read = (name: string, unsetList: string[]): string | undefined => {
    const raw = env[name];
    if (raw !== undefined && raw !== '') return raw;
    unsetList.push(name);
    return undefined;
  };

  const readNumeric = (name: string, fallback: number, isInteger: boolean): number => {
    const raw = read(name, defaulted);
    if (raw === undefined) return fallback;
    const parsed = Number(raw);
    const isValid = isInteger ? Number.isInteger(parsed) : Number.isFinite(parsed);
    if (!isValid) throw new Error(`${name} must be ${isInteger ? 'an integer' : 'a number'}, got "${raw}"`);
    return parsed;
  };

  return {
    optional: (name) => read(name, defaulted),
    required: (name) => read(name, missingRequired) ?? '',
    integer: (name, fallback) => readNumeric(name, fallback, true),
    number: (name, fallback) => readNumeric(name, fallback, false),
    report: () => ({ missingRequired: [...missingRequired], defaulted: [...defaulted] }),
  };
};

const readServerConfig = (reader: EnvReader): ServerConfig => {
  const nodeEnv = reader.optional('NODE_ENV') ?? DEFAULT_NODE_ENV;
  const isProduction = nodeEnv === PRODUCTION_NODE_ENV;
  const defaultLogLevel = isProduction ? DEFAULT_PRODUCTION_LOG_LEVEL : DEFAULT_DEVELOPMENT_LOG_LEVEL;
  return {
    port: reader.integer('PORT', DEFAULT_PORT),
    nodeEnv,
    isProduction,
    logLevel: reader.optional('LOG_LEVEL') ?? defaultLogLevel,
  };
};

const readHttpConfig = (reader: EnvReader): HttpConfig => ({
  corsOrigins: reader.optional('CORS_ORIGIN')?.split(CORS_ORIGIN_SEPARATOR) ?? false,
  rateLimit: {
    windowMs: reader.integer('RATE_LIMIT_WINDOW_MS', DEFAULT_RATE_LIMIT_WINDOW_MS),
    limit: reader.integer('RATE_LIMIT_MAX', DEFAULT_RATE_LIMIT_MAX),
  },
  streamRateLimit: {
    windowMs: reader.integer('STREAM_RATE_LIMIT_WINDOW_MS', DEFAULT_STREAM_RATE_LIMIT_WINDOW_MS),
    limit: reader.integer('STREAM_RATE_LIMIT_MAX', DEFAULT_STREAM_RATE_LIMIT_MAX),
  },
});

const readMongoConfig = (reader: EnvReader): MongoConfig => ({
  uri: reader.required('MONGODB_URI'),
  database: reader.optional('MONGODB_DATABASE') ?? DEFAULT_MONGODB_DATABASE,
  collection: reader.optional('MONGODB_COLLECTION') ?? DEFAULT_CHUNK_COLLECTION,
  metaDatabase: reader.optional('MONGODB_META_DB_NAME') ?? DEFAULT_MONGODB_META_DATABASE,
  timeoutMs: reader.integer('MONGODB_TIMEOUT', DEFAULT_MONGODB_TIMEOUT_MS),
});

const readQdrantConfig = (reader: EnvReader): QdrantConfig => ({
  url: reader.optional('QDRANT_URL') ?? DEFAULT_QDRANT_URL,
  fallbackCollection: reader.optional('QDRANT_COLLECTION') ?? DEFAULT_CHUNK_COLLECTION,
});

const readEmbeddingConfig = (reader: EnvReader): EmbeddingConfig => ({
  serviceUrl: reader.optional('EMBEDDING_SERVICE_URL') ?? DEFAULT_EMBEDDING_SERVICE_URL,
  modelName: reader.optional('EMBEDDING_MODEL_NAME') ?? DEFAULT_EMBEDDING_MODEL_NAME,
  timeoutMs: reader.integer('EMBEDDING_SERVICE_TIMEOUT', DEFAULT_EMBEDDING_TIMEOUT_MS),
});

const readLlmConfig = (reader: EnvReader): LlmConfig => ({
  apiUrl: reader.required('LLM_API_ENDPOINT'),
  apiKey: reader.required('LLM_API_KEY'),
  model: reader.required('LLM_MODEL'),
  temperature: reader.number('LLM_TEMPERATURE', DEFAULT_LLM_TEMPERATURE),
  maxTokens: reader.integer('LLM_MAX_TOKENS', DEFAULT_LLM_MAX_TOKENS),
  timeoutMs: reader.integer('LLM_TIMEOUT', DEFAULT_LLM_TIMEOUT_MS),
  systemPrompt: reader.optional('SYSTEM_PROMPT') ?? DEFAULT_SYSTEM_PROMPT,
});

const readRetrievalConfig = (reader: EnvReader): RetrievalConfig => ({
  topK: reader.integer('RETRIEVAL_TOP_K', DEFAULT_RETRIEVAL_TOP_K),
  minScore: reader.number('RETRIEVAL_MIN_SCORE', DEFAULT_RETRIEVAL_MIN_SCORE),
});

/**
 * @throws Error naming the variable when a numeric variable does not parse
 */
export const loadConfig = (env: Environment): LoadedConfig => {
  const reader = createEnvReader(env);
  const config: AppConfig = {
    server: readServerConfig(reader),
    http: readHttpConfig(reader),
    mongo: readMongoConfig(reader),
    qdrant: readQdrantConfig(reader),
    embedding: readEmbeddingConfig(reader),
    llm: readLlmConfig(reader),
    retrieval: readRetrievalConfig(reader),
  };
  return { config, report: reader.report() };
};

const loaded = loadConfig(process.env);

export const config: AppConfig = loaded.config;
export const environmentReport: EnvironmentReport = loaded.report;
