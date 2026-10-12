import { parseExplanationRequest } from '../../validation/explanationRequest';

const QUESTION = 'Que dit cet article ?';

describe('parseExplanationRequest', () => {
  it('accepts a selection and a segment that ends with a question', () => {
    const body = { selection: ['LEGIARTI1'], messages: [{ role: 'user', content: QUESTION }] };

    expect(parseExplanationRequest(body)).toEqual({ isValid: true, request: body });
  });

  it('accepts an empty selection: the LLM then asks for documents', () => {
    const body = { selection: [], messages: [{ role: 'user', content: QUESTION }] };

    expect(parseExplanationRequest(body)).toEqual({ isValid: true, request: body });
  });

  it.each([
    ['a repeated document', { selection: ['A', 'A'], messages: [{ role: 'user', content: QUESTION }] }, 'selection'],
    ['no message', { selection: ['A'], messages: [] }, 'messages'],
    ['a segment that ends with an answer', { selection: ['A'], messages: [{ role: 'assistant', content: 'x' }] }, 'messages'],
    ['a system message', { selection: ['A'], messages: [{ role: 'system', content: QUESTION }] }, 'messages.0.role'],
    ['a body that is not an object', 'texte', 'body'],
  ])('refuses %s, without quoting the question', (_case, body, field) => {
    const parsed = parseExplanationRequest(body);

    expect(parsed.isValid).toBe(false);
    if (parsed.isValid) return;
    expect(parsed.issues.map((issue) => issue.field)).toContain(field);
    expect(JSON.stringify(parsed.issues)).not.toContain(QUESTION);
  });
});
