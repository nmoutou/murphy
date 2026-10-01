import Image from 'next/image';

/** Décorative : l'élément englobant porte le nom accessible */
interface IconProps {
  readonly icon: string;
  readonly size: number;
  readonly animated?: boolean;
  readonly negative?: boolean;
}

export default function Icon({ icon, size, animated = false, negative = false }: IconProps) {
  const src = animated ? `/icons/animated/${icon}.gif` : `/icons/static/${icon}.png`;
  // Icônes noires sur thème sombre : inversées, sauf sur fond clair
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
