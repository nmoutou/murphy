import { safeValidateUIMessages, TypeValidationError } from 'ai';
import type { AppUIMessage } from '@murphy/contract/messages';
import { appDataPartSchemas, appMessageMetadataSchema } from '@murphy/contract/messages';

export interface ValidationIssue {
  readonly field: string;
  readonly message: string;
}

export type ChatRequestParseResult =
  | { readonly isValid: true; readonly messages: AppUIMessage[] }
  | { readonly isValid: false; readonly issues: ValidationIssue[] };

interface SchemaIssue {
  readonly path: readonly unknown[];
  readonly message: string;
}

const MESSAGES_FIELD = 'messages';
const MISSING_MESSAGES = 'messages must be provided';

// Un message utilisateur n'a pas de métadonnée : seul le `ragTiming` de l'assistant est vérifié
const MESSAGE_METADATA_SCHEMA = appMessageMetadataSchema.optional();

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

const isSchemaIssue = (value: unknown): value is SchemaIssue =>
  isRecord(value) && Array.isArray(value.path) && typeof value.message === 'string';

const schemaIssuesOf = (cause: unknown): SchemaIssue[] =>
  isRecord(cause) && Array.isArray(cause.issues) ? cause.issues.filter(isSchemaIssue) : [];

const fieldOf = (base: string, path: readonly unknown[]): string =>
  path.reduce<string>((field, key) => (typeof key === 'number' ? `${field}[${key}]` : `${field}.${String(key)}`), base);

/**
 * Le message d'erreur du SDK embarque toute la valeur reçue, conversation comprise :
 * on ne garde que les champs et les messages du schéma
 */
const toValidationIssues = (error: Error): ValidationIssue[] => {
  if (!TypeValidationError.isInstance(error)) return [{ field: MESSAGES_FIELD, message: MISSING_MESSAGES }];

  const base = error.context?.field ?? MESSAGES_FIELD;
  const issues = schemaIssuesOf(error.cause).map((issue) => ({ field: fieldOf(base, issue.path), message: issue.message }));
  if (issues.length > 0) return issues;
  // Part de données sans schéma : la cause est la phrase du SDK
  return [{ field: base, message: typeof error.cause === 'string' ? error.cause : 'invalid value' }];
};

export const parseChatRequest = async (body: unknown): Promise<ChatRequestParseResult> => {
  const validation = await safeValidateUIMessages<AppUIMessage>({
    messages: isRecord(body) ? body.messages : undefined,
    dataSchemas: appDataPartSchemas,
    metadataSchema: MESSAGE_METADATA_SCHEMA,
  });
  if (validation.success) return { isValid: true, messages: validation.data };
  return { isValid: false, issues: toValidationIssues(validation.error) };
};
