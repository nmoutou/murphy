import crypto from 'crypto';

interface ApiMeta {
  timestamp: string;
  traceId: string;
}

function buildMeta(): ApiMeta {
  return {
    timestamp: new Date().toISOString(),
    traceId: crypto.randomUUID(),
  };
}

export function buildApiResponse<T>(code: number, message: string, data?: T) {
  return {
    status: { code, message },
    ...(data !== undefined ? { data } : {}),
    meta: buildMeta(),
  };
}
