import { useEffect, useRef } from "react";

interface KeyComboListenerProps {
    onCombo: (combo: string) => void;
}

export default function KeyComboListener({ onCombo }: KeyComboListenerProps){
    const keysPressed = useRef<Set<string>>(new Set());

    useEffect(() => {
        // Ajout d'une touche
        function keyOnHandler(e: KeyboardEvent){
            keysPressed.current.add(e.code);
        }

        // Suppresion d'une touche
        function keyOffHandler(e: KeyboardEvent){
            let combo = false;
            
            combo = combos.welcomeLayout.every(key => keysPressed.current.has(key));
            if (combo) { onCombo("welcomeLayout"); }

            combo = combos.chatLayout.every(key => keysPressed.current.has(key));
            if (combo) { onCombo("chatLayout"); }


            keysPressed.current.delete(e.code);
        }

        // Ajout des observateurs
        document.addEventListener("keydown", keyOnHandler);
        document.addEventListener("keyup", keyOffHandler);

        // Définitions des combos
        // /!\ Changer de place /!\
        const combos = {
            "welcomeLayout": ["AltLeft", "Numpad0"],
            "chatLayout": ["AltLeft", "Numpad1"],
        };
        
    }, [onCombo])

    return (
        <div/>
    );
}