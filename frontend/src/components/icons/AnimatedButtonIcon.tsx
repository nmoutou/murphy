import ButtonIcon, { ButtonIconProps } from "./ButtonIcon";

type AnimatedButtonIconProps = Omit<ButtonIconProps, "animatedOnHover">;

export default function AnimatedButtonIcon(props: AnimatedButtonIconProps){
    return <ButtonIcon {...props} animatedOnHover />
}