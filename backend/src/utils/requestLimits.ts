/**
 * Request Limits
 * A chat request is read up to the same size, whatever its transport
 */

/** 100 KiB, `express.json()`'s default, also the chat WebSocket's `maxPayload` */
export const MAX_REQUEST_BODY_BYTES = 102_400;
