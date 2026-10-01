import { useState } from 'react';
import Icon from './Icon';

type ButtonIconVariant = 'primary' | 'secondary';

interface ButtonIconProps {
  readonly icon: string;
  /** Nom accessible du bouton : l'icône est décorative */
  readonly label: string;
  readonly size: number;
  /** Facultatif pour un bouton submit, géré par son formulaire */
  readonly onClick?: () => void;
  readonly type?: 'button' | 'submit';
  readonly variant?: ButtonIconVariant;
  readonly animatedOnHover?: boolean;
}

export default function ButtonIcon({
  icon,
  label,
  size,
  onClick,
  type = 'button',
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
      type={type}
      aria-label={label}
      className={`p-1 rounded-full transition-all ${background} ${opacity}`}
      onPointerEnter={() => setIsHovered(true)}
      onPointerLeave={() => setIsHovered(false)}
      onClick={onClick}
    >
      <Icon icon={icon} size={size} animated={animated} negative={isNegative} />
    </button>
  );
}

export type { ButtonIconProps, ButtonIconVariant };
