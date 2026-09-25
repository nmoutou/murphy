/**
 * API Client for RAG Backend Communication
 */

import { APIError } from '@/types/errors';

const DEFAULT_TIMEOUT = 30000; // 30 seconds

/**
 * Get the base URL for API requests
 */
function getBaseURL(): string {
  // In development, API server runs on port 5000
  // In production, should be configured via environment
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
}

/**
 * Generic API request handler with error handling
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit & { timeout?: number; signal?: AbortSignal } = {}
): Promise<T> {
  const { timeout = DEFAULT_TIMEOUT, signal: userSignal, ...restOptions } = options;

  // Create AbortController for timeout if no signal provided
  const controller = new AbortController();
  let timeoutId: NodeJS.Timeout | undefined;

  if (!userSignal) {
    timeoutId = setTimeout(() => controller.abort(), timeout);
  }

  const finalSignal = userSignal || controller.signal;

  try {
    const response = await fetch(`${getBaseURL()}${endpoint}`, {
      ...restOptions,
      signal: finalSignal,
      headers: {
        'Content-Type': 'application/json',
        ...restOptions.headers,
      },
    });

    if (!response.ok) {
      const errorData: APIError = {
        message: response.statusText,
        code: String(response.status),
      };

      try {
        const jsonData = await response.json() as any;
        if (jsonData?.status?.message) {
          errorData.message = jsonData.status.message;
        }
        if (jsonData?.errors) {
          errorData.details = jsonData.errors;
        }
      } catch {
        // Could not parse error response as JSON
      }

      throw errorData;
    }

    const data = (await response.json()) as T;
    return data;
  } catch (error) {
    // Handle AbortError
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw {
        message: `Request timeout after ${timeout}ms`,
        code: 'TIMEOUT',
      };
    }

    // Re-throw API errors
    if (error && typeof error === 'object' && 'message' in error) {
      throw error;
    }

    // Network errors
    throw {
      message: error instanceof Error ? error.message : 'Network request failed',
      code: 'NETWORK_ERROR',
    };
  } finally {
    if (!userSignal && timeoutId) {
      clearTimeout(timeoutId);
    }
  }
}

/**
 * Health check endpoint
 */
export async function checkHealth(
  signal?: AbortSignal
): Promise<{ status: 'ok' | 'degraded' | 'down'; services: Record<string, string> }> {
  const response = await apiRequest<any>('/api/v1/health', { method: 'GET', signal });
  return response.data;
}

export type { APIError };
