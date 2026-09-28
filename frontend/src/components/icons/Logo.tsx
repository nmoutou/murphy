import Image from 'next/image';
import Link from 'next/link';

// The image's proportions: 14 units wide for 3 high
const LOGO_WIDTH_UNITS = 14;
const LOGO_HEIGHT_UNITS = 3;
const LOGO_RATIO = LOGO_HEIGHT_UNITS / LOGO_WIDTH_UNITS;
const LOGO_DEFAULT_WIDTH = 355;

interface LogoProps {
  readonly width?: number;
}

export default function Logo({ width = LOGO_DEFAULT_WIDTH }: LogoProps) {
  const height = width * LOGO_RATIO;

  return (
    <Link href="/">
      <Image
        className="px-16 w-auto h-auto invert"
        src={'/img/logo.png'}
        alt={'Logo Murphy'}
        width={width}
        height={height}
        priority
      />
    </Link>
  );
}
