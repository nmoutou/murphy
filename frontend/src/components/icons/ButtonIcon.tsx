import { useState } from 'react';
import Icon from './Icon';

type ButtonIconVariant = 'primary' | 'secondary';

interface ButtonIconProps {
  icon: string;
  alt: string;
  size: number;
  onClick: () => void;
  variant?: ButtonIconVariant;
  animatedOnHover?: boolean;
}

export default function ButtonIcon({
  icon,
  alt,
  size,
  onClick,
  variant = 'secondary',
  animatedOnHover = false,
}: ButtonIconProps) {
  const [isHovered, setIsHovered] = useState(false);

  const isNegative = variant === 'primary' ? true : isHovered;
  const background = isHovered || variant === 'primary' ? 'bg-quaternary' : 'bg-transparent';
  const opacity = isHovered ? 'opacity-80' : 'opacity-100';
  const animated = animatedOnHover ? isHovered : false;

  return (
    <button
      className={`p-1 rounded-full transition-all ${background} ${opacity}`}
      onPointerEnter={() => setIsHovered(true)}
      onPointerLeave={() => setIsHovered(false)}
      onClick={onClick}
    >
      <Icon icon={icon} alt={alt} size={size} animated={animated} negative={isNegative} />
    </button>
  );
}

export type { ButtonIconProps, ButtonIconVariant };
