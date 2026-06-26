import { WebSocketServer, WebSocket } from 'ws';
import { logger as rootLogger } from '../utils/logger';
import { createChatStream } from '../services/chatService';
import type { AppUIMessage } from '../types/messages';

const logger = rootLogger.child({ context: 'chatWebSocket' });

export function registerChatWebSocket(wss: WebSocketServer): void {
  wss.on('connection', (ws: WebSocket) => {
    logger.info('WebSocket client connected');

    ws.once('message', async (raw: Buffer | ArrayBuffer | Buffer[]) => {
      try {
        const payload = JSON.parse(raw.toString()) as { messages?: AppUIMessage[] };
        const stream = await createChatStream(payload.messages || []);
        const reader = stream.getReader();

        ws.on('close', () => {
          reader.cancel().catch(() => undefined);
        });

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          ws.send(JSON.stringify(value));
        }

        ws.close();
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        ws.send(JSON.stringify({ type: 'error', errorText: message }));
        ws.close();
      }
    });
  });
}
