/**
 * Seul lecteur de `process.env`, une fois au démarrage. Le lecteur note les variables
 * absentes ou par défaut : `checkEnvironment` rend compte de ce qui a vraiment été lu.
 *
 * Aucun import interne hors `envReader` : `utils/logger.ts` dépend de ce module.
 */

import type { EnvReader, Environment, EnvironmentReport } from './envReader';
import { createEnvReader } from './envReader';

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
  readonly searchRateLimit: RateLimitConfig;
  /** Par IP, en plus du limiteur général */
  readonly explanationRateLimit: RateLimitConfig;
  /** Tous clients confondus, sur 24 h : borne la dépense en LLM */
  readonly explanationDailyLimit: number;
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
  /** Préfixe complet, collé tel quel devant la question ; rien devant les passages indexés */
  readonly queryInstruction: string;
}

export interface PaginationConfig {
  /** Les tailles de page permises, la première par défaut */
  readonly sizes: readonly number[];
  /** Documents classés par chaque sous-requête avant la fusion : à garder d'une page à l'autre */
  readonly depth: number;
}

/** Un serveur compatible OpenAI ; le code ne nomme aucun fournisseur */
export interface LlmConfig {
  readonly baseUrl: string;
  readonly apiKey: string;
  readonly model: string;
  /** Jusqu'au premier fragment de la réponse, pas jusqu'à sa fin */
  readonly timeoutMs: number;
  /** En points de code : textes, métadonnées, prompt et segment de conversation */
  readonly contextMaxChars: number;
  readonly maxOutputTokens: number;
}

export interface AppConfig {
  readonly server: ServerConfig;
  readonly http: HttpConfig;
  readonly mongo: MongoConfig;
  readonly opensearch: OpenSearchConfig;
  readonly embedding: EmbeddingConfig;
  readonly pagination: PaginationConfig;
  readonly llm: LlmConfig;
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
const DEFAULT_RATE_LIMIT_MAX = 600;
const DEFAULT_SEARCH_RATE_LIMIT_WINDOW_MS = 60_000;
const DEFAULT_SEARCH_RATE_LIMIT_MAX = 60;
const DEFAULT_MONGODB_DATABASE = 'MURPHY_DATA';
const DEFAULT_MONGODB_TIMEOUT_MS = 10_000;
const DEFAULT_OPENSEARCH_URL = 'http://opensearch:9200';
const DEFAULT_OPENSEARCH_TIMEOUT_MS = 10_000;
const DEFAULT_EMBEDDING_SERVICE_URL = 'http://embedding-service:80';
const DEFAULT_EMBEDDING_MODEL_NAME = 'microsoft/harrier-oss-v1-0.6b';
const DEFAULT_EMBEDDING_TIMEOUT_MS = 10_000;
/** Sous la forme de la variable, découpé comme elle */
const DEFAULT_PAGINATION_SIZES = '10,25,50';
const DEFAULT_PAGINATION_DEPTH = 100;
/** Le plafond du `k` d'un kNN, et `index.max_result_window` par défaut */
const MAX_PAGINATION_DEPTH = 10_000;
const DEFAULT_EXPLANATION_RATE_LIMIT_WINDOW_MS = 60_000;
const DEFAULT_EXPLANATION_RATE_LIMIT_MAX = 10;
const DEFAULT_EXPLANATION_DAILY_LIMIT = 200;
const DEFAULT_LLM_TIMEOUT_MS = 30_000;
const DEFAULT_LLM_CONTEXT_MAX_CHARS = 100_000;
const DEFAULT_LLM_MAX_OUTPUT_TOKENS = 2_000;

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
  searchRateLimit: {
    windowMs: reader.integer('SEARCH_RATE_LIMIT_WINDOW_MS', DEFAULT_SEARCH_RATE_LIMIT_WINDOW_MS),
    limit: reader.integer('SEARCH_RATE_LIMIT_MAX', DEFAULT_SEARCH_RATE_LIMIT_MAX),
  },
  explanationRateLimit: {
    windowMs: reader.integer('EXPLANATION_RATE_LIMIT_WINDOW_MS', DEFAULT_EXPLANATION_RATE_LIMIT_WINDOW_MS),
    limit: reader.integer('EXPLANATION_RATE_LIMIT_MAX', DEFAULT_EXPLANATION_RATE_LIMIT_MAX),
  },
  explanationDailyLimit: reader.integer('EXPLANATION_DAILY_LIMIT', DEFAULT_EXPLANATION_DAILY_LIMIT),
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
  queryInstruction: reader.required('EMBEDDING_QUERY_INSTRUCTION'),
});

/** @throws si une taille manque, se répète, n'est pas positive ou dépasse la profondeur */
const assertPageSizes = ({ sizes, depth }: PaginationConfig): void => {
  if (sizes.length === 0) throw new Error('PAGINATION_SIZES must list at least one page size');
  if (new Set(sizes).size !== sizes.length) {
    throw new Error(`PAGINATION_SIZES must not repeat a size, got ${sizes.join(',')}`);
  }
  const invalid = sizes.find((size) => size < 1 || size > depth);
  if (invalid !== undefined) {
    throw new Error(`Each of PAGINATION_SIZES must be between 1 and PAGINATION_DEPTH (${depth}), got ${invalid}`);
  }
};

/** @throws si la profondeur est hors de [1, 10 000], ou si une taille de page est invalide */
const assertPagination = (pagination: PaginationConfig): void => {
  const { depth } = pagination;
  if (depth < 1) throw new Error(`PAGINATION_DEPTH must be positive, got ${depth}`);
  if (depth > MAX_PAGINATION_DEPTH) {
    throw new Error(`PAGINATION_DEPTH (${depth}) must not exceed ${MAX_PAGINATION_DEPTH}, the OpenSearch k-NN limit`);
  }
  assertPageSizes(pagination);
};

const readPaginationConfig = (reader: EnvReader): PaginationConfig => {
  const pagination = {
    sizes: reader.integerList('PAGINATION_SIZES', DEFAULT_PAGINATION_SIZES),
    depth: reader.integer('PAGINATION_DEPTH', DEFAULT_PAGINATION_DEPTH),
  };
  assertPagination(pagination);
  return pagination;
};

/** @throws en nommant la variable si l'une d'elles n'est pas strictement positive */
const readLlmConfig = (reader: EnvReader): LlmConfig => ({
  baseUrl: reader.required('LLM_BASE_URL'),
  apiKey: reader.required('LLM_API_KEY'),
  model: reader.required('LLM_MODEL'),
  timeoutMs: reader.positiveInteger('LLM_TIMEOUT', DEFAULT_LLM_TIMEOUT_MS),
  contextMaxChars: reader.positiveInteger('LLM_CONTEXT_MAX_CHARS', DEFAULT_LLM_CONTEXT_MAX_CHARS),
  maxOutputTokens: reader.positiveInteger('LLM_MAX_OUTPUT_TOKENS', DEFAULT_LLM_MAX_OUTPUT_TOKENS),
});

/**
 * @throws en nommant la variable quand une variable numérique est malformée, ou quand
 * la pagination ou le LLM sont incohérents
 */
export const loadConfig = (env: Environment): LoadedConfig => {
  const reader = createEnvReader(env);
  const config: AppConfig = {
    server: readServerConfig(reader),
    http: readHttpConfig(reader),
    mongo: readMongoConfig(reader),
    opensearch: readOpenSearchConfig(reader),
    embedding: readEmbeddingConfig(reader),
    pagination: readPaginationConfig(reader),
    llm: readLlmConfig(reader),
  };
  return { config, report: reader.report() };
};

const loaded = loadConfig(process.env);

export const config: AppConfig = loaded.config;
export const environmentReport: EnvironmentReport = loaded.report;

export type { EnvironmentReport };
