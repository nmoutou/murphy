import { useState } from "react";
import Icon from "./Icon";
import { useTheme } from "../providers/ThemeProvider";

type ButtonIconVariant = "primary" | "secondary"

interface ButtonIconProps {
    icon: string
    alt: string
    size: number
    onClick: () => void
    variant?: ButtonIconVariant
    animatedOnHover?: boolean
}

export default function ButtonIcon({
    icon,
    alt,
    size,
    onClick,
    variant = "secondary",
    animatedOnHover = false,
}: ButtonIconProps){
    const theme = useTheme();
    const [isHovered, setIsHovered] = useState(false);

    const isNegative = variant === "primary" ? true : isHovered;
    const backgroundColor = (isHovered || variant === "primary") ? theme.colors.quaternary : "transparent";
    const opacity = isHovered ? "80%" : "100%";
    const animated = animatedOnHover ? isHovered : false;

    return (
        <button
            className="p-1 rounded-full transition-all"
            style={{ backgroundColor, opacity }}
            onPointerEnter={() => setIsHovered(true)}
            onPointerLeave={() => setIsHovered(false)}
            onClick={onClick}
        >
            <Icon
                icon={icon}
                alt={alt}
                size={size}
                animated={animated}
                negative={isNegative}
            />
        </button>
    );
}

export type { ButtonIconProps, ButtonIconVariant };
