import { useState } from 'react';
import Icon from './Icon';

interface AnimatedIconProps {
  icon: string;
  alt: string;
  size: number;
  negative?: boolean;
}

export default function AnimatedIcon({ icon, alt, size, negative = false }: AnimatedIconProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div onPointerEnter={() => setIsHovered(true)} onPointerLeave={() => setIsHovered(false)}>
      <Icon animated={isHovered} icon={icon} alt={alt} size={size} negative={negative} />
    </div>
  );
}
