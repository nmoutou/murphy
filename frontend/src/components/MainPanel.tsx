"use client";

import { useCallback } from "react";
import { useTheme } from "./providers/ThemeProvider";
import WelcomeLayout from "./layouts/WelcomeLayout";
import ChatLayout from "./layouts/ChatLayout";
import ChatBox from "./ChatBox";
import { useRagChat } from "@/hooks/useRagChat";
import type { DocumentChunk } from "@murphy/contract/messages";

export default function MainPanel(){
    const theme = useTheme();
    const { messages, sendMessage, stop, status } = useRagChat();
    const isLoading = status === 'submitted' || status === 'streaming';

    const handleQuery = useCallback(
        async (question: string) => {
            await sendMessage({ text: question });
        },
        [sendMessage]
    );

    const handleSourceClick = useCallback((chunk: DocumentChunk) => {
        // TODO: Implement source expansion/modal
    }, []);

    const handleCopy = useCallback((content: string) => {
        // Optional: Add notification here
    }, []);
    
    return (
        <div
            style={{ backgroundColor: theme.colors.primary }}
            className="min-h-screen w-full flex flex-col items-center relative"
        >
            {/* Chat messages or welcome */}
            { messages.length > 0 ? (
                <div className="flex-1 min-h-0 w-full flex justify-center items-start py-4 overflow-y-auto scrollbar">
                    <ChatLayout 
                        messages={messages}
                        status={status}
                        onSourceClick={handleSourceClick}
                        onCopy={handleCopy}
                    />
                </div>
            ) : (
                <div className="flex-1 w-full flex flex-col justify-center items-center">
                    <WelcomeLayout/>
                    <ChatBox
                        onEnter={handleQuery}
                        onCancel={stop}
                        disabled={isLoading}
                        absolute={false}
                    />
                </div>
            )}

            {/* Chat input for messages view */}
            { messages.length > 0 && (
                <ChatBox
                    onEnter={handleQuery}
                    onCancel={stop}
                    disabled={isLoading}
                    absolute={true}
                />
            )}
        </div>
    );
}