/** Seule l'URL de base du backend est configurée ; le chemin de la socket est celui du backend. */

const DEFAULT_BACKEND_URL = 'http://localhost:5000';
const CHAT_SOCKET_PATH = '/api/v1/chat/ws';
const SECURE_HTTP_PROTOCOL = 'https:';

export const getChatSocketUrl = (): string => {
  // Lu littéralement : Next n'inline que `process.env.NEXT_PUBLIC_*` écrit en entier
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || DEFAULT_BACKEND_URL;

  let socketUrl: URL;
  try {
    socketUrl = new URL(CHAT_SOCKET_PATH, backendUrl);
  } catch {
    throw new Error(`NEXT_PUBLIC_API_URL n'est pas une URL valide : "${backendUrl}"`);
  }

  socketUrl.protocol = socketUrl.protocol === SECURE_HTTP_PROTOCOL ? 'wss:' : 'ws:';
  return socketUrl.toString();
};
