import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Workspace from '@/features/workspace/Workspace';
import { fetchDocument } from '@/lib/api/documents';
import { explanationChat, SUMMARY_REQUEST } from '@/stores/explanationStore';
import { useSearchStore } from '@/stores/searchStore';
import { useSelectionStore } from '@/stores/selectionStore';

vi.mock('@/lib/api/documents', () => ({ fetchDocument: vi.fn() }));

const SELECTED = {
  identifier: 'LEGIARTI000049431213',
  title: 'Article 2224',
  documentType: 'article' as const,
  contentLength: 53,
};

const GROUP_SELECTOR = '.dv-groupview';

const closeButton = (title: string) =>
  screen.getByRole('button', { name: `Fermer l'onglet ${title}` });

const queryCloseButton = (title: string) =>
  screen.queryByRole('button', { name: `Fermer l'onglet ${title}` });

const renderWorkspace = () => {
  const { container } = render(<Workspace />);
  return { groupCount: () => container.querySelectorAll(GROUP_SELECTOR).length };
};

const closeTabs = async (...titles: string[]) => {
  for (const title of titles) await userEvent.click(closeButton(title));
};

beforeEach(() => {
  useSearchStore.setState({ contextBudget: 100_000 });
  useSelectionStore.setState({ entries: [SELECTED] });
  vi.mocked(fetchDocument).mockResolvedValue({
    identifier: SELECTED.identifier,
    title: SELECTED.title,
    content: 'Les actions personnelles se prescrivent par cinq ans.',
    contentLength: 53,
  });
});

const sidebar = () => within(screen.getByRole('complementary', { name: 'Sélection' }));

describe('Workspace', () => {
  it('opens Recherche, Graphe and Explications in one group, Recherche active', () => {
    const { groupCount } = renderWorkspace();

    expect(groupCount()).toBe(1);
    for (const title of ['Recherche', 'Graphe', 'Explications']) {
      expect(closeButton(title)).toBeInTheDocument();
    }
    expect(screen.getByRole('region', { name: 'Recherche' })).toHaveClass('dv-active-group');
  });

  it('gives each tab its full title as a tooltip', () => {
    renderWorkspace();

    expect(closeButton('Explications').closest('[title]')).toHaveAttribute('title', 'Explications');
  });

  it('keeps a hidden tab in the page, so it keeps its scroll position', async () => {
    explanationChat.messages = [];
    renderWorkspace();

    await userEvent.click(screen.getByRole('tab', { name: 'Explications' }));
    const conversation = await screen.findByText(/Posez une question/);
    const results = screen.getByRole('tab', { name: 'Recherche' });
    await userEvent.click(results);
    await vi.waitFor(() => expect(results).toHaveAttribute('aria-selected', 'true'));

    expect(conversation).toBeInTheDocument();
  });

  it('reopens a closed fixed tab from the group menu', async () => {
    renderWorkspace();
    await closeTabs('Graphe');

    await userEvent.click(screen.getByRole('button', { name: 'Rouvrir un onglet' }));
    await userEvent.click(screen.getByRole('button', { name: 'Ouvrir Graphe' }));

    expect(closeButton('Graphe')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Graphe' })).not.toBeInTheDocument();
  });

  it('says so when every fixed tab is open', async () => {
    renderWorkspace();

    await userEvent.click(screen.getByRole('button', { name: 'Rouvrir un onglet' }));

    expect(screen.getByText('Tous les onglets sont ouverts.')).toBeInTheDocument();
  });

  it('offers the closed tabs once the workspace is empty', async () => {
    renderWorkspace();

    await closeTabs('Recherche', 'Graphe', 'Explications');
    const watermark = screen.getByText(/Aucun onglet ouvert/).parentElement;
    if (!watermark) throw new Error('The watermark has no container');
    await userEvent.click(within(watermark).getByRole('button', { name: 'Ouvrir Recherche' }));

    expect(queryCloseButton('Recherche')).toBeInTheDocument();
  });

  it('asks for a summary from « Résumer », reopening the Explications tab once closed', async () => {
    const summary = 'data: {"type":"start","messageId":"a1"}\n\ndata: [DONE]\n\n';
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(summary)));
    explanationChat.messages = [];
    renderWorkspace();
    await closeTabs('Explications');

    await act(() => userEvent.click(sidebar().getByRole('button', { name: 'Résumer' })));

    expect(closeButton('Explications')).toBeInTheDocument();
    expect(await screen.findByText(SUMMARY_REQUEST)).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it('opens a selected document in a tab, with no passage to highlight', async () => {
    renderWorkspace();

    await act(() => userEvent.click(sidebar().getByRole('button', { name: SELECTED.title })));

    expect(closeButton(SELECTED.title)).toBeInTheDocument();
    expect(await screen.findByText(/se prescrivent par cinq ans/)).toBeInTheDocument();
    expect(document.querySelector('mark')).toBeNull();
  });
});
