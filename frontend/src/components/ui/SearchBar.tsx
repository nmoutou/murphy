'use client';

import AnimatedButtonIcon from '@/components/icons/AnimatedButtonIcon';
import { useSearchInput } from './useSearchInput';

const PLACEHOLDER = "Nul n'est censé ignorer la loi.";
const CENTERED_ICON_SIZE = 32;
const HEADER_ICON_SIZE = 24;

type SearchBarVariant = 'centered' | 'header';

interface VariantStyle {
  readonly formClasses: string;
  readonly iconSize: number;
}

const VARIANT_STYLES: Record<SearchBarVariant, VariantStyle> = {
  centered: { formClasses: 'mx-8 w-full max-w-[600px] p-3', iconSize: CENTERED_ICON_SIZE },
  header: { formClasses: 'flex-1 min-w-0 px-3 py-1', iconSize: HEADER_ICON_SIZE },
};

interface SearchBarProps {
  readonly onSubmit: (question: string) => void;
  readonly initialQuestion?: string;
  readonly variant: SearchBarVariant;
}

export default function SearchBar({ onSubmit, initialQuestion = '', variant }: SearchBarProps) {
  const { question, handleChange, handleSubmit } = useSearchInput(onSubmit, initialQuestion);
  const { formClasses, iconSize } = VARIANT_STYLES[variant];

  return (
    <form
      role="search"
      onSubmit={handleSubmit}
      className={`flex items-center gap-2 rounded-[25px] bg-secondary ${formClasses}`}
    >
      <input
        name="question"
        aria-label="Votre question"
        className="w-full bg-transparent px-2 font-mono text-tertiary placeholder:italic focus:outline-none truncate"
        placeholder={PLACEHOLDER}
        onChange={handleChange}
        value={question}
        autoComplete="off"
      />
      <AnimatedButtonIcon
        icon="globe"
        label="Lancer la recherche"
        size={iconSize}
        type="submit"
        variant="primary"
      />
    </form>
  );
}
