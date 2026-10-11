import { searchRequestSchema } from '@murphy/contract/search';

export interface ValidationIssue {
  readonly field: string;
  readonly message: string;
}

/** Une requête dont la taille de page est résolue : celle demandée, ou la première permise */
export interface PagedSearchRequest {
  readonly question: string;
  readonly page: number;
  readonly pageSize: number;
}

export type SearchRequestParseResult =
  | { readonly isValid: true; readonly request: PagedSearchRequest }
  | { readonly isValid: false; readonly issues: ValidationIssue[] };

/** Un corps qui n'est pas un objet n'a pas de chemin */
const BODY_FIELD = 'body';
const PAGE_SIZE_FIELD = 'pageSize';
const SIZE_SEPARATOR = ', ';

/**
 * Les messages de zod ne citent pas la valeur reçue : la question n'en sort pas
 * @param pageSizes les tailles permises, la première par défaut
 */
export const parseSearchRequest = (body: unknown, pageSizes: readonly number[]): SearchRequestParseResult => {
  const parsed = searchRequestSchema.safeParse(body);
  if (!parsed.success) {
    const issues = parsed.error.issues.map(({ path, message }) => ({ field: path.join('.') || BODY_FIELD, message }));
    return { isValid: false, issues };
  }
  const { question, page, pageSize = pageSizes[0] } = parsed.data;
  if (!pageSizes.includes(pageSize)) {
    const message = `must be one of ${pageSizes.join(SIZE_SEPARATOR)}`;
    return { isValid: false, issues: [{ field: PAGE_SIZE_FIELD, message }] };
  }
  return { isValid: true, request: { question, page, pageSize } };
};
