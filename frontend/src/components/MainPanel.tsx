'use client';

import { useCallback } from 'react';
import WelcomeLayout from './layouts/WelcomeLayout';
import ChatLayout from './layouts/ChatLayout';
import ChatBox from './ChatBox';
import ErrorDialog from './chat/ErrorDialog';
import { useRagChat } from '@/hooks/useRagChat';

export default function MainPanel() {
  const { messages, sendMessage, stop, status, errorStage, clearError } = useRagChat();
  const isLoading = status === 'submitted' || status === 'streaming';
  const errorDialog = errorStage && <ErrorDialog stage={errorStage} onClose={clearError} />;

  const handleQuery = useCallback(
    async (question: string) => {
      await sendMessage({ text: question });
    },
    [sendMessage],
  );

  return (
    <div className="min-h-screen w-full flex flex-col items-center relative bg-primary">
      {/* Chat messages or welcome */}
      {messages.length > 0 ? (
        <div className="flex-1 min-h-0 w-full flex justify-center items-start py-4 overflow-y-auto scrollbar">
          <ChatLayout messages={messages} />
        </div>
      ) : (
        <div className="flex-1 w-full flex flex-col justify-center items-center">
          <WelcomeLayout />
          <ChatBox onEnter={handleQuery} onCancel={stop} disabled={isLoading} absolute={false} />
        </div>
      )}

      {/* Chat input for messages view */}
      {messages.length > 0 && (
        <ChatBox onEnter={handleQuery} onCancel={stop} disabled={isLoading} absolute={true} />
      )}

      {errorDialog}
    </div>
  );
}
