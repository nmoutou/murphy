import type { SearchRequest } from '@murphy/contract/search';
import { searchRequestSchema } from '@murphy/contract/search';

export interface ValidationIssue {
  readonly field: string;
  readonly message: string;
}

export type SearchRequestParseResult =
  | { readonly isValid: true; readonly request: SearchRequest }
  | { readonly isValid: false; readonly issues: ValidationIssue[] };

/** Un corps qui n'est pas un objet n'a pas de chemin */
const BODY_FIELD = 'body';

/** Les messages de zod ne citent pas la valeur reçue : la question n'en sort pas */
export const parseSearchRequest = (body: unknown): SearchRequestParseResult => {
  const parsed = searchRequestSchema.safeParse(body);
  if (parsed.success) return { isValid: true, request: parsed.data };
  const issues = parsed.error.issues.map(({ path, message }) => ({ field: path.join('.') || BODY_FIELD, message }));
  return { isValid: false, issues };
};
