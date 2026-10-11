import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import DocumentIcon from '@/features/results/DocumentIcon';

const iconSource = (name: string) =>
  screen.getByRole('img', { name }).querySelector('img')?.getAttribute('src');

describe('DocumentIcon', () => {
  it('picks the icon of the type, named by the type', () => {
    render(<DocumentIcon documentType="article" />);

    expect(iconSource('Article')).toBe('/icons/static/doc.png');
  });

  it('picks the icon of a known nature first', () => {
    render(<DocumentIcon documentType="texte" nature="CODE" />);

    expect(iconSource('Texte · CODE')).toBe('/icons/static/folder.png');
  });

  it('falls back on the type for an unknown nature', () => {
    render(<DocumentIcon documentType="decision" nature="QPC" />);

    expect(iconSource('Décision · QPC')).toBe('/icons/static/window.png');
  });
});
