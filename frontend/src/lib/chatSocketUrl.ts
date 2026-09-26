/**
 * Where the browser opens the chat WebSocket. Only the backend base URL is
 * configured (`NEXT_PUBLIC_API_URL`); the socket path is the backend's.
 */

const DEFAULT_BACKEND_URL = 'http://localhost:5000';
const CHAT_SOCKET_PATH = '/api/v1/chat/ws';
const SECURE_HTTP_PROTOCOL = 'https:';

export const getChatSocketUrl = (): string => {
  // Read literally: Next only inlines `process.env.NEXT_PUBLIC_*` written out in full
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
