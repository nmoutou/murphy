/**
 * Lit un environnement en notant les variables absentes ou par défaut. Aucun import
 * interne : `config.ts` en dépend, et `utils/logger.ts` dépend de `config.ts`.
 */

export type Environment = Readonly<Record<string, string | undefined>>;

export interface EnvironmentReport {
  /** Variables obligatoires absentes : la fonctionnalité correspondante ne marche pas */
  readonly missingRequired: readonly string[];
  /** Variables facultatives absentes : leur défaut s'applique */
  readonly defaulted: readonly string[];
}

const LIST_SEPARATOR = ',';

export interface EnvReader {
  /** Absente → `undefined`, notée « par défaut » */
  readonly optional: (name: string) => string | undefined;
  /** Absente → `''`, notée « manquante » */
  readonly required: (name: string) => string;
  /** @throws si la valeur n'est pas un entier */
  readonly integer: (name: string, fallback: number) => number;
  /** @throws si la valeur n'est pas un entier strictement positif */
  readonly positiveInteger: (name: string, fallback: number) => number;
  /** Entiers séparés par des virgules ; @throws si l'un d'eux n'en est pas un */
  readonly integerList: (name: string, fallback: string) => readonly number[];
  readonly report: () => EnvironmentReport;
}

const parseInteger = (name: string, raw: string): number => {
  const parsed = Number(raw);
  if (raw.trim() === '' || !Number.isInteger(parsed)) throw new Error(`${name} must be an integer, got "${raw}"`);
  return parsed;
};

const assertPositive = (name: string, value: number): number => {
  if (value < 1) throw new Error(`${name} must be positive, got ${value}`);
  return value;
};

export const createEnvReader = (env: Environment): EnvReader => {
  const missingRequired: string[] = [];
  const defaulted: string[] = [];

  // Compose passe `VAR=` quand la variable manque à `.env.dev` : vide = absente
  const read = (name: string, unsetList: string[]): string | undefined => {
    const raw = env[name];
    if (raw !== undefined && raw !== '') return raw;
    unsetList.push(name);
    return undefined;
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
    positiveInteger: (name, fallback) => assertPositive(name, readInteger(name, fallback)),
    integerList: readIntegerList,
    report: () => ({ missingRequired: [...missingRequired], defaulted: [...defaulted] }),
  };
};
