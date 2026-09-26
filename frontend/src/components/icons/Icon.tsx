import Image from 'next/image';

/** Decorative: the element around the icon carries the accessible name */
interface IconProps {
  readonly icon: string;
  readonly size: number;
  readonly animated?: boolean;
  readonly negative?: boolean;
}

export default function Icon({ icon, size, animated = false, negative = false }: IconProps) {
  const src = animated ? `/icons/animated/${icon}.gif` : `/icons/static/${icon}.png`;
  // Black icons on a dark theme: inverted, unless drawn on a light background
  const inversion = negative ? '' : 'invert';

  return (
    <Image
      aria-hidden
      className={inversion}
      src={src}
      alt=""
      width={size}
      height={size}
      unoptimized
    />
  );
}
