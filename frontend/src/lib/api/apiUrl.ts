const DEFAULT_BACKEND_URL = 'http://localhost:5000';
const API_BASE_PATH = '/api/v1';

/** Seule l'origine du backend est configurée ; le préfixe des routes est le sien */
export const buildApiUrl = (path: string): string => {
  // Lu littéralement : Next n'inline que `process.env.NEXT_PUBLIC_*` écrit en entier
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || DEFAULT_BACKEND_URL;
  try {
    return new URL(`${API_BASE_PATH}${path}`, backendUrl).toString();
  } catch {
    throw new Error(`NEXT_PUBLIC_API_URL n'est pas une URL valide : "${backendUrl}"`);
  }
};
