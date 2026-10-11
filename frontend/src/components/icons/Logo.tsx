import Image from 'next/image';
import Link from 'next/link';

// Proportions de l'image : 14 de large pour 3 de haut
const LOGO_WIDTH_UNITS = 14;
const LOGO_HEIGHT_UNITS = 3;
const LOGO_RATIO = LOGO_HEIGHT_UNITS / LOGO_WIDTH_UNITS;
const LOGO_DEFAULT_WIDTH = 355;

interface LogoProps {
  readonly width?: number;
}

export default function Logo({ width = LOGO_DEFAULT_WIDTH }: LogoProps) {
  // Entière : next/image prend une hauteur arrondie par le navigateur pour une retouche CSS
  const height = Math.round(width * LOGO_RATIO);

  return (
    <Link href="/">
      <Image
        className="h-auto invert"
        src={'/img/logo.png'}
        alt={'Logo Murphy'}
        width={width}
        height={height}
        priority
      />
    </Link>
  );
}
