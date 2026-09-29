import crypto from 'crypto';

interface ApiMeta {
  timestamp: string;
  traceId: string;
}

const buildMeta = (): ApiMeta => ({
  timestamp: new Date().toISOString(),
  traceId: crypto.randomUUID(),
});

export const buildApiResponse = <T>(code: number, message: string, data?: T) => ({
  status: { code, message },
  ...(data !== undefined ? { data } : {}),
  meta: buildMeta(),
});
