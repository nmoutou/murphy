import { useState } from 'react';
import Icon from './Icon';

interface AnimatedIconProps {
  readonly icon: string;
  readonly size: number;
  readonly negative?: boolean;
}

export default function AnimatedIcon({ icon, size, negative = false }: AnimatedIconProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div onPointerEnter={() => setIsHovered(true)} onPointerLeave={() => setIsHovered(false)}>
      <Icon animated={isHovered} icon={icon} size={size} negative={negative} />
    </div>
  );
}
