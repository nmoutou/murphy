import type { ExplanationRequest } from '@murphy/contract/explanations';
import type { ValidationIssue } from './searchRequest';
import { explanationRequestSchema } from '@murphy/contract/explanations';

export type ExplanationRequestParseResult =
  | { readonly isValid: true; readonly request: ExplanationRequest }
  | { readonly isValid: false; readonly issues: ValidationIssue[] };

/** Un corps qui n'est pas un objet n'a pas de chemin */
const BODY_FIELD = 'body';

/** Les messages de zod ne citent pas la valeur reçue : ni question ni réponse n'en sortent */
export const parseExplanationRequest = (body: unknown): ExplanationRequestParseResult => {
  const parsed = explanationRequestSchema.safeParse(body);
  if (parsed.success) return { isValid: true, request: parsed.data };
  const issues = parsed.error.issues.map(({ path, message }) => ({ field: path.join('.') || BODY_FIELD, message }));
  return { isValid: false, issues };
};
