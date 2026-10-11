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
  readonly searchRateLimit: RateLimitConfig;
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

export interface AppConfig {
  readonly server: ServerConfig;
  readonly http: HttpConfig;
  readonly mongo: MongoConfig;
  readonly opensearch: OpenSearchConfig;
  readonly embedding: EmbeddingConfig;
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
const LIST_SEPARATOR = ',';
const DEFAULT_PAGINATION_DEPTH = 100;
/** Le plafond du `k` d'un kNN, et `index.max_result_window` par défaut */
const MAX_PAGINATION_DEPTH = 10_000;

interface EnvReader {
  /** Absente → `undefined`, notée « par défaut » */
  readonly optional: (name: string) => string | undefined;
  /** Absente → `''`, notée « manquante » */
  readonly required: (name: string) => string;
  /** @throws si la valeur n'est pas un entier */
  readonly integer: (name: string, fallback: number) => number;
  /** Entiers séparés par des virgules ; @throws si l'un d'eux n'en est pas un */
  readonly integerList: (name: string, fallback: string) => readonly number[];
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

  const parseInteger = (name: string, raw: string): number => {
    const parsed = Number(raw);
    if (raw.trim() === '' || !Number.isInteger(parsed)) throw new Error(`${name} must be an integer, got "${raw}"`);
    return parsed;
  };

  const readInteger = (name: string, fallback: number): number => {
    const raw = read(name, defaulted);
    return raw === undefined ? fallback : parseInteger(name, raw);
  };

  const readIntegerList = (name: string, fallback: string): readonly number[] => {
    const raw = read(name, defaulted) ?? fallback;
    return raw.split(LIST_SEPARATOR).map((value) => parseInteger(name, value));
  };

  return {
    optional: (name) => read(name, defaulted),
    required: (name) => read(name, missingRequired) ?? '',
    integer: readInteger,
    integerList: readIntegerList,
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
  searchRateLimit: {
    windowMs: reader.integer('SEARCH_RATE_LIMIT_WINDOW_MS', DEFAULT_SEARCH_RATE_LIMIT_WINDOW_MS),
    limit: reader.integer('SEARCH_RATE_LIMIT_MAX', DEFAULT_SEARCH_RATE_LIMIT_MAX),
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
  queryInstruction: reader.required('EMBEDDING_QUERY_INSTRUCTION'),
});

/** @throws si une taille manque, se répète, n'est pas positive ou dépasse la profondeur */
const assertPageSizes = ({ sizes, depth }: PaginationConfig): void => {
  if (sizes.length === 0) throw new Error('PAGINATION_SIZES must list at least one page size');
  if (new Set(sizes).size !== sizes.length) {
    throw new Error(`PAGINATION_SIZES must not repeat a size, got ${sizes.join(LIST_SEPARATOR)}`);
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
    pagination: readPaginationConfig(reader),
  };
  return { config, report: reader.report() };
};

const loaded = loadConfig(process.env);

export const config: AppConfig = loaded.config;
export const environmentReport: EnvironmentReport = loaded.report;
