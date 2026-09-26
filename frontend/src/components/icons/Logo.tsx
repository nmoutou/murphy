import Image from 'next/image';
import Link from 'next/link';

const LOGO_RATIO = 3 / 14;
const LOGO_DEFAULT_WIDTH = 355;

export default function Logo({ width = LOGO_DEFAULT_WIDTH }) {
  const height = LOGO_DEFAULT_WIDTH * LOGO_RATIO;

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
