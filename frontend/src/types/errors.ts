export interface APIError {
  message: string;
  code?: string;
  details?: unknown;
}