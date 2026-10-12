import type { ExplanationRequest } from '@murphy/contract/explanations';
import type { ExplainedDocument } from '../types/explanation';
import type { LlmAnswer, LlmMessage } from '../infra/llm';
import { readFileSync } from 'fs';
import { join } from 'path';
import { config } from '../config';
import { getInfraClients } from '../infra/clients';
import { RagError } from '../types/rag';
import { EXPLAINED_METADATA_KEYS, renderDocuments } from './explanationContext';
import { countCodePoints, mergeConsecutiveUserMessages } from './explanationMessages';

/** Copié dans `dist/` au build ; lu une fois, au chargement : absent, le démarrage échoue */
const EXPLANATION_PROMPT = readFileSync(join(__dirname, '..', 'prompts', 'explanation.md'), 'utf8');
const DOCUMENTS_HEADING = '# Documents fournis';
const NO_DOCUMENT = 'Aucun document sélectionné.';
const SECTION_SEPARATOR = '\n\n';
/** Le nom que `toRagError` et le client reconnaissent comme un délai dépassé */
const TIMEOUT_ERROR_NAME = 'TimeoutError';

export interface PreparedExplanation {
  readonly instructions: string;
  readonly messages: readonly LlmMessage[];
  readonly documentCount: number;
  /** En points de code : prompt, documents et segment */
  readonly contextLength: number;
}

export interface OpenedAnswer {
  /** Le premier fragment, ou la fin si le LLM n'a rien écrit ou si le client est parti */
  readonly first: IteratorResult<string, unknown>;
  readonly rest: LlmAnswer;
}

const buildInstructions = (documents: readonly ExplainedDocument[]): string =>
  [EXPLANATION_PROMPT.trim(), DOCUMENTS_HEADING, documents.length > 0 ? renderDocuments(documents) : NO_DOCUMENT].join(
    SECTION_SEPARATOR,
  );

const measureContext = (instructions: string, messages: readonly LlmMessage[]): number =>
  messages.reduce((total, { content }) => total + countCodePoints(content), countCodePoints(instructions));

/**
 * Le serveur fait foi sur le budget : la jauge du client ne compte que les textes
 * @throws RagError `DOCUMENT_NOT_FOUND`, `CONTEXT_TOO_LARGE`, ou celle de la lecture
 */
export const prepareExplanation = async ({ selection, messages }: ExplanationRequest): Promise<PreparedExplanation> => {
  const documents = await getInfraClients().mongo.fetchExplainedDocuments(selection, EXPLAINED_METADATA_KEYS);
  const instructions = buildInstructions(documents);
  const merged = mergeConsecutiveUserMessages(messages);
  const contextLength = measureContext(instructions, merged);
  const budget = config.llm.contextMaxChars;
  if (contextLength > budget) {
    throw new RagError('request', 'CONTEXT_TOO_LARGE', `The context has ${contextLength} code points, above the budget of ${budget}`);
  }
  return { instructions, messages: merged, documentCount: documents.length, contextLength };
};

/**
 * Lance le LLM et attend son premier fragment, au plus `LLM_TIMEOUT` : une panne se
 * dit encore par un statut HTTP, avant que le flux ne parte
 * @param clientSignal levé quand le client part : l'appel au LLM est coupé
 * @throws RagError `LLM_FAILED`, ou `TIMEOUT` sans premier fragment à temps
 */
export const openAnswer = async (prepared: PreparedExplanation, clientSignal: AbortSignal): Promise<OpenedAnswer> => {
  const { timeoutMs } = config.llm;
  const firstFragmentTimeout = new AbortController();
  const timer = setTimeout(
    () => firstFragmentTimeout.abort(new DOMException(`No fragment within ${timeoutMs} ms`, TIMEOUT_ERROR_NAME)),
    timeoutMs,
  );
  const signal = AbortSignal.any([clientSignal, firstFragmentTimeout.signal]);
  const rest = getInfraClients().llm.streamAnswer({ instructions: prepared.instructions, messages: prepared.messages, signal });
  try {
    const first = await rest.next();
    if (firstFragmentTimeout.signal.aborted) {
      throw new RagError('generation', 'TIMEOUT', `The LLM sent no fragment within ${timeoutMs} ms`);
    }
    return { first, rest };
  } finally {
    clearTimeout(timer);
  }
};
