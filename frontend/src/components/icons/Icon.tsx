import Image from 'next/image';

interface IconProps {
  icon: string;
  alt: string;
  size: number;
  animated?: boolean;
  negative?: boolean;
}

export default function Icon({ icon, alt, size, animated = false, negative = false }: IconProps) {
  const src = animated ? `/icons/animated/${icon}.gif` : `/icons/static/${icon}.png`;
  // Black icons on a dark theme: inverted, unless drawn on a light background
  const inversion = negative ? '' : 'invert';

  return (
    <Image
      aria-hidden
      className={inversion}
      src={src}
      alt={alt}
      width={size}
      height={size}
      unoptimized
    />
  );
}
