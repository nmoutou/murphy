/**
 * Seul lecteur de `process.env`, une fois au démarrage. Le lecteur note les variables
 * absentes ou par défaut : `checkEnvironment` rend compte de ce qui a vraiment été lu.
 *
 * Aucun import interne ici : `utils/logger.ts` dépend de ce module.
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
  readonly timeoutMs: number;
}

export interface OpenSearchConfig {
  readonly url: string;
  /** Écrit par l'ingestion, qui lit la même variable `OPENSEARCH_INDEX` */
  readonly index: string;
  /** Par requête ; le défaut du client est de 30 s */
  readonly timeoutMs: number;
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
  readonly timeoutMs: number;
  readonly systemPrompt: string;
}

/** Une seule page est servie tant que le LLM reste branché (ADR-028 §10) */
export interface PaginationConfig {
  /** Documents par page */
  readonly size: number;
  /** Documents classés par chaque sous-requête avant la fusion : à garder d'une page à l'autre */
  readonly depth: number;
}

export interface AppConfig {
  readonly server: ServerConfig;
  readonly http: HttpConfig;
  readonly mongo: MongoConfig;
  readonly opensearch: OpenSearchConfig;
  readonly embedding: EmbeddingConfig;
  readonly llm: LlmConfig;
  readonly pagination: PaginationConfig;
}

export interface EnvironmentReport {
  /** Variables obligatoires absentes : la fonctionnalité correspondante ne marche pas */
  readonly missingRequired: readonly string[];
  /** Variables facultatives absentes : leur défaut s'applique */
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
const DEFAULT_MONGODB_DATABASE = 'MURPHY_DATA';
const DEFAULT_MONGODB_TIMEOUT_MS = 10_000;
const DEFAULT_OPENSEARCH_URL = 'http://opensearch:9200';
const DEFAULT_OPENSEARCH_TIMEOUT_MS = 10_000;
const DEFAULT_EMBEDDING_SERVICE_URL = 'http://embedding-service:80';
const DEFAULT_EMBEDDING_MODEL_NAME = 'all-mpnet-base-v2';
const DEFAULT_EMBEDDING_TIMEOUT_MS = 10_000;
const DEFAULT_LLM_TEMPERATURE = 0.7;
const DEFAULT_LLM_TIMEOUT_MS = 30_000;
const DEFAULT_PAGINATION_SIZE = 10;
const DEFAULT_PAGINATION_DEPTH = 100;
/** Le plafond du `k` d'un kNN, et `index.max_result_window` par défaut */
const MAX_PAGINATION_DEPTH = 10_000;
const DEFAULT_SYSTEM_PROMPT =
  'Vous êtes un assistant juridique intelligent spécialisé dans le droit français. ' +
  "Répondez aux questions de l'utilisateur en vous basant sur les documents juridiques fournis. " +
  'Soyez précis, professionnel et citez les sources pertinentes. ' +
  'Si la réponse ne se trouve pas dans les documents fournis, dites-le clairement.';

interface EnvReader {
  /** Absente → `undefined`, notée « par défaut » */
  readonly optional: (name: string) => string | undefined;
  /** Absente → `''`, notée « manquante » */
  readonly required: (name: string) => string;
  /** @throws si la valeur n'est pas un entier */
  readonly integer: (name: string, fallback: number) => number;
  /** @throws si la valeur n'est pas un nombre fini */
  readonly number: (name: string, fallback: number) => number;
  readonly report: () => EnvironmentReport;
}

const createEnvReader = (env: Environment): EnvReader => {
  const missingRequired: string[] = [];
  const defaulted: string[] = [];

  // Compose passe `VAR=` quand la variable manque à `.env.dev` : vide = absente
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
    logLevel: reader.optional('NODE_LOG_LEVEL') ?? defaultLogLevel,
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
  timeoutMs: reader.integer('MONGODB_TIMEOUT', DEFAULT_MONGODB_TIMEOUT_MS),
});

const readOpenSearchConfig = (reader: EnvReader): OpenSearchConfig => ({
  url: reader.optional('OPENSEARCH_URL') ?? DEFAULT_OPENSEARCH_URL,
  index: reader.required('OPENSEARCH_INDEX'),
  timeoutMs: reader.integer('OPENSEARCH_TIMEOUT', DEFAULT_OPENSEARCH_TIMEOUT_MS),
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
  timeoutMs: reader.integer('LLM_TIMEOUT', DEFAULT_LLM_TIMEOUT_MS),
  systemPrompt: reader.optional('SYSTEM_PROMPT') ?? DEFAULT_SYSTEM_PROMPT,
});

/** @throws si une valeur n'est pas un entier positif, ou si la profondeur est hors de [taille, 10 000] */
const assertPagination = ({ size, depth }: PaginationConfig): void => {
  if (size < 1 || depth < 1) {
    throw new Error(`PAGINATION_SIZE and PAGINATION_DEPTH must be positive, got ${size} and ${depth}`);
  }
  if (depth < size) {
    throw new Error(`PAGINATION_DEPTH (${depth}) must be at least PAGINATION_SIZE (${size})`);
  }
  if (depth > MAX_PAGINATION_DEPTH) {
    throw new Error(`PAGINATION_DEPTH (${depth}) must not exceed ${MAX_PAGINATION_DEPTH}, the OpenSearch k-NN limit`);
  }
};

const readPaginationConfig = (reader: EnvReader): PaginationConfig => {
  const pagination = {
    size: reader.integer('PAGINATION_SIZE', DEFAULT_PAGINATION_SIZE),
    depth: reader.integer('PAGINATION_DEPTH', DEFAULT_PAGINATION_DEPTH),
  };
  assertPagination(pagination);
  return pagination;
};

/**
 * @throws en nommant la variable quand une variable numérique est malformée, ou quand
 * la pagination est incohérente
 */
export const loadConfig = (env: Environment): LoadedConfig => {
  const reader = createEnvReader(env);
  const config: AppConfig = {
    server: readServerConfig(reader),
    http: readHttpConfig(reader),
    mongo: readMongoConfig(reader),
    opensearch: readOpenSearchConfig(reader),
    embedding: readEmbeddingConfig(reader),
    llm: readLlmConfig(reader),
    pagination: readPaginationConfig(reader),
  };
  return { config, report: reader.report() };
};

const loaded = loadConfig(process.env);

export const config: AppConfig = loaded.config;
export const environmentReport: EnvironmentReport = loaded.report;
