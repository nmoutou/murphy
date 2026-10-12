import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SelectionSidebar from '@/features/selection/SelectionSidebar';
import { useSearchStore } from '@/stores/searchStore';
import type { SelectionEntry } from '@/stores/selectionStore';
import { useSelectionStore } from '@/stores/selectionStore';

const BUDGET = 1_000;

const entryOf = (identifier: string, contentLength = 100): SelectionEntry => ({
  identifier,
  title: `Titre ${identifier}`,
  documentType: 'article',
  isInForce: true,
  contentLength,
});

const select = (...entries: SelectionEntry[]) => act(() => useSelectionStore.setState({ entries }));

const renderSidebar = ({ isAnswering = false } = {}) => {
  const onSummarize = vi.fn();
  const onOpenDocument = vi.fn();
  render(
    <SelectionSidebar
      isAnswering={isAnswering}
      onSummarize={onSummarize}
      onOpenDocument={onOpenDocument}
    />,
  );
  const sidebar = within(screen.getByRole('complementary', { name: 'Sélection' }));
  return { sidebar, onSummarize, onOpenDocument };
};

beforeEach(() => {
  useSelectionStore.setState(useSelectionStore.getInitialState(), true);
  useSearchStore.setState({ contextBudget: BUDGET });
});

describe('SelectionSidebar', () => {
  it('invites to add documents from the search, summarizing disabled', () => {
    const { sidebar } = renderSidebar();

    expect(sidebar.getByText(/Ajoutez des documents depuis la recherche/)).toBeInTheDocument();
    expect(sidebar.getByRole('button', { name: 'Résumer' })).toBeDisabled();
  });

  it('numbers the documents in order, and renumbers them after a removal', async () => {
    select(entryOf('A'), entryOf('B'), entryOf('C'));
    const { sidebar } = renderSidebar();

    await userEvent.click(sidebar.getByRole('button', { name: 'Retirer Titre A de la sélection' }));

    const items = sidebar.getAllByRole('listitem');
    expect(items.map((item) => item.textContent)).toEqual([
      expect.stringMatching(/^1.*Titre B/),
      expect.stringMatching(/^2.*Titre C/),
    ]);
  });

  it('summarizes and opens a document through its callbacks', async () => {
    select(entryOf('A'));
    const { sidebar, onSummarize, onOpenDocument } = renderSidebar();

    await userEvent.click(sidebar.getByRole('button', { name: 'Résumer' }));
    await userEvent.click(sidebar.getByRole('button', { name: 'Titre A' }));

    expect(onSummarize).toHaveBeenCalledOnce();
    expect(onOpenDocument).toHaveBeenCalledExactlyOnceWith(entryOf('A'));
  });

  it('accepts a selection over budget, turns the gauge red and blocks summarizing', () => {
    select(entryOf('A', 800), entryOf('B', 400));
    const { sidebar } = renderSidebar();

    expect(sidebar.getByRole('meter', { name: 'Budget de lecture' })).toHaveAttribute(
      'aria-valuetext',
      'Budget dépassé (120 %) : retirez un document.',
    );
    expect(sidebar.getByRole('button', { name: 'Résumer' })).toBeDisabled();
  });

  it('shows the share of the budget the texts use', () => {
    select(entryOf('A', 250));
    const { sidebar } = renderSidebar();

    expect(sidebar.getByText('25 % du budget de lecture')).toBeInTheDocument();
  });

  it('blocks summarizing while an answer is coming', () => {
    select(entryOf('A'));
    const { sidebar } = renderSidebar({ isAnswering: true });

    expect(sidebar.getByRole('button', { name: 'Résumer' })).toBeDisabled();
  });

  it('removes every document at once', async () => {
    select(entryOf('A'), entryOf('B'));
    const { sidebar } = renderSidebar();

    await userEvent.click(sidebar.getByRole('button', { name: 'Tout retirer' }));

    expect(useSelectionStore.getState().entries).toEqual([]);
  });

  it('collapses to its counter, and unfolds again', async () => {
    select(entryOf('A'), entryOf('B'));
    const { sidebar } = renderSidebar();

    await userEvent.click(sidebar.getByRole('button', { name: 'Replier la sélection' }));
    expect(sidebar.queryByRole('list')).not.toBeInTheDocument();

    await userEvent.click(sidebar.getByRole('button', { name: 'Déplier la sélection (2)' }));
    expect(sidebar.getByRole('list', { name: 'Documents sélectionnés' })).toBeInTheDocument();
  });

  it('opens as a drawer from its floating button on small screens', async () => {
    select(entryOf('A'));
    renderSidebar();

    await userEvent.click(screen.getByRole('button', { name: 'Afficher la sélection (1)' }));

    expect(screen.getAllByRole('complementary', { name: 'Sélection' })).toHaveLength(2);
    await userEvent.click(screen.getByRole('button', { name: 'Fermer la sélection' }));
    expect(screen.getAllByRole('complementary', { name: 'Sélection' })).toHaveLength(1);
  });
});
