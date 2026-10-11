import type { DisplayedErrorCode } from '@/lib/api/apiError';

const REQUEST_REFUSED = "La recherche n'a pas pu être lancée.";
const RATE_LIMITED = 'Trop de recherches : réessayez dans une minute.';
const DOCUMENT_MISSING = 'Ce document est introuvable.';
const SERVICE_DOWN = 'Le service de recherche est indisponible.';
const INTERNAL_FAILURE = 'Une erreur interne est survenue.';

/** Un code ajouté au contrat casse le build tant qu'il n'a pas de message */
export const ERROR_MESSAGES: Record<DisplayedErrorCode, string> = {
  VALIDATION_ERROR: REQUEST_REFUSED,
  INVALID_JSON: REQUEST_REFUSED,
  INVALID_REQUEST_BODY: REQUEST_REFUSED,
  PAYLOAD_TOO_LARGE: REQUEST_REFUSED,
  PAGE_OUT_OF_RANGE: REQUEST_REFUSED,
  SEARCH_RATE_LIMIT_EXCEEDED: RATE_LIMITED,
  RATE_LIMIT_EXCEEDED: RATE_LIMITED,
  DOCUMENT_NOT_FOUND: DOCUMENT_MISSING,
  NOT_FOUND: DOCUMENT_MISSING,
  EMBEDDING_FAILED: SERVICE_DOWN,
  SEARCH_FAILED: SERVICE_DOWN,
  DB_FETCH_FAILED: SERVICE_DOWN,
  TIMEOUT: SERVICE_DOWN,
  CONTRACT_VIOLATION: INTERNAL_FAILURE,
  INTERNAL: INTERNAL_FAILURE,
  NETWORK: 'Le serveur est injoignable.',
};
