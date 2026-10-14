import { describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/react';
import { useRef } from 'react';
import type { ExplanationUIMessage } from '@/lib/api/explanationRequest';
import { useScrollToLastQuestion } from '@/features/explanation/useScrollToLastQuestion';

const message = (id: string, role: 'user' | 'assistant'): ExplanationUIMessage => ({
  id,
  role,
  parts: [{ type: 'text', text: id }],
});

function Panel({ messages }: { readonly messages: readonly ExplanationUIMessage[] }) {
  const panelRef = useRef<HTMLElement>(null);
  useScrollToLastQuestion(panelRef, messages);
  return (
    <section ref={panelRef}>
      {messages.map(({ id, role }) =>
        role === 'user' ? <p key={id} data-question /> : <p key={id} />,
      )}
    </section>
  );
}

describe('useScrollToLastQuestion', () => {
  it('scrolls when a question is sent, not while its answer streams', () => {
    const scrollTo = vi.spyOn(Element.prototype, 'scrollTo');
    const { rerender } = render(<Panel messages={[]} />);
    expect(scrollTo).not.toHaveBeenCalled();

    rerender(<Panel messages={[message('q1', 'user')]} />);
    expect(scrollTo).toHaveBeenCalledOnce();

    rerender(<Panel messages={[message('q1', 'user'), message('a1', 'assistant')]} />);
    expect(scrollTo).toHaveBeenCalledOnce();

    rerender(
      <Panel
        messages={[message('q1', 'user'), message('a1', 'assistant'), message('q2', 'user')]}
      />,
    );
    expect(scrollTo).toHaveBeenCalledTimes(2);
  });
});
