import { DefaultChatTransport } from 'ai';
import type { ExplanationUIMessage } from './explanationRequest';
import { toExplanationRequest } from './explanationRequest';
import { ApiError } from './apiError';
import { buildApiUrl } from './apiUrl';
import { readErrorCode, readJson } from './request';

const EXPLANATIONS_PATH = '/explanations';

/** Un refus avant le flux (budget, plafond, LLM en panne) garde son code, comme ailleurs */
const fetchExplanation: typeof fetch = async (input, init) => {
  let response: Response;
  try {
    response = await fetch(input, init);
  } catch (error) {
    if (init?.signal?.aborted) throw error;
    throw new ApiError('NETWORK', `POST ${EXPLANATIONS_PATH}: ${String(error)}`);
  }
  if (!response.ok) {
    const code = readErrorCode(await readJson(response));
    throw new ApiError(code, `HTTP ${response.status} on ${EXPLANATIONS_PATH}`);
  }
  return response;
};

/** Le SSE de l'AI SDK, en `POST` : la question ne passe jamais par l'URL */
export const createExplanationTransport = (): DefaultChatTransport<ExplanationUIMessage> =>
  new DefaultChatTransport<ExplanationUIMessage>({
    fetch: fetchExplanation,
    // Calculée à l'envoi : une URL invalide échoue comme une requête, pas au chargement
    prepareSendMessagesRequest: ({ messages }) => ({
      api: buildApiUrl(EXPLANATIONS_PATH),
      body: toExplanationRequest(messages),
    }),
  });
