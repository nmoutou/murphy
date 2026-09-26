import Image from 'next/image';
import Link from 'next/link';
import { useTheme } from '../providers/ThemeProvider';

const LOGO_RATIO = 3 / 14;
const LOGO_DEFAULT_WIDTH = 355;

export default function Logo({ width = LOGO_DEFAULT_WIDTH }) {
  const height = LOGO_DEFAULT_WIDTH * LOGO_RATIO;
  const theme = useTheme();

  return (
    <Link href="/">
      <Image
        className={`px-16 w-auto h-auto ${theme.name === 'dark' ? 'invert' : ''}`}
        src={'/img/logo.png'}
        alt={'Logo Murphy'}
        width={width}
        height={height}
        priority
      />
    </Link>
  );
}
