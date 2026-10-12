/** 100 Kio : le défaut d'`express.json()` */
export const MAX_REQUEST_BODY_BYTES = 102_400;

/** Un `\uXXXX` échappé, que bien des clients JSON écrivent pour tout caractère non ASCII */
const MAX_JSON_BYTES_PER_CODE_POINT = 6;
/** Les identifiants de la sélection et la structure JSON */
const EXPLANATION_BODY_MARGIN_BYTES = MAX_REQUEST_BODY_BYTES;

/** Un long segment doit être compté par le budget (`CONTEXT_TOO_LARGE`), pas refusé avant */
export const toExplanationBodyLimit = (contextMaxChars: number): number =>
  contextMaxChars * MAX_JSON_BYTES_PER_CODE_POINT + EXPLANATION_BODY_MARGIN_BYTES;
