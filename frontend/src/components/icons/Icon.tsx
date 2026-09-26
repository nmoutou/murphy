import { useTheme } from '@/components/providers/ThemeProvider';
import Image from 'next/image';

interface IconProps {
  icon: string;
  alt: string;
  size: number;
  animated?: boolean;
  negative?: boolean;
}

export default function Icon({ icon, alt, size, animated = false, negative = false }: IconProps) {
  const theme = useTheme();

  const src = animated ? `/icons/animated/${icon}.gif` : `/icons/static/${icon}.png`;
  const dark = theme.name === 'dark' && !negative ? 'invert' : '';

  return (
    <Image
      aria-hidden
      className={dark}
      src={src}
      alt={alt}
      width={size}
      height={size}
      unoptimized
    />
  );
}
