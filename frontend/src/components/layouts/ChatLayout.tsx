"use client";

import { useEffect, useRef } from "react";
import UserMessage from "@/components/chat/UserMessage";
import AIMessage from "@/components/chat/AIMessage";
import ErrorMessage from "@/components/chat/ErrorMessage";
import type { AppUIMessage, DocumentChunk } from "@murphy/contract/messages";

interface ChatLayoutProps {
    messages: Array<AppUIMessage>
    status?: 'submitted' | 'streaming' | 'ready' | 'error'
    onSourceClick?: (chunk: DocumentChunk) => void
    onCopy?: (content: string) => void
}

export default function ChatLayout({ messages, status, onSourceClick, onCopy }: ChatLayoutProps){
    const hasHistory = messages.length > 2;

    const lastUserRef = useRef<HTMLDivElement | null>(null);
    const lastMessage = messages[messages.length - 1];

    useEffect(() => {
        if (lastMessage?.role === "user") {
            lastUserRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }, [lastMessage]);

    return (
        <div
            className={`w-[70%] min-w-[310px] flex flex-col gap-4 ${hasHistory ? "pb-[90vh]" : "pb-0"}`}
        >
            {messages.map((message, index) => {
                const isLastUser = message.role === "user" && index === messages.length - 1;
                const ref = isLastUser ? lastUserRef : undefined;
                const style = isLastUser ? { scrollMarginTop: "16px" } : undefined;

                return (
                    <div key={message.id ?? index} ref={ref} style={style}>
                        {message.role === "user" ? (
                            <UserMessage message={message} />
                        ) : message.parts?.some((part) => part.type === 'text' && part.text.startsWith("❌")) ? (
                            <ErrorMessage message={message.parts.map((part) => part.type === 'text' ? part.text : '').join('')} />
                        ) : (
                            <AIMessage
                                message={message}
                                onSourceClick={onSourceClick}
                                onCopy={onCopy}
                            />
                        )}
                    </div>
                );
            })}


        </div>
    );
}