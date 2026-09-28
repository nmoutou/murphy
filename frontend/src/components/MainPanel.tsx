'use client';

import WelcomeLayout from './layouts/WelcomeLayout';
import ChatLayout from './layouts/ChatLayout';
import ChatBox from './ChatBox';
import ErrorDialog from './chat/ErrorDialog';
import { useRagChat } from '@/hooks/useRagChat';

export default function MainPanel() {
  const { messages, sendMessage, stop, status, errorStage, clearError } = useRagChat();
  const isLoading = status === 'submitted' || status === 'streaming';
  const hasMessages = messages.length > 0;

  const handleQuery = async (question: string) => {
    await sendMessage({ text: question });
  };

  // Centred under the welcome, then docked under the conversation
  const chatBox = (
    <ChatBox onEnter={handleQuery} onCancel={stop} disabled={isLoading} isDocked={hasMessages} />
  );

  return (
    <div className="min-h-screen w-full flex flex-col items-center relative bg-primary">
      {hasMessages ? (
        <div className="flex-1 min-h-0 w-full flex justify-center items-start py-4 overflow-y-auto scrollbar">
          <ChatLayout messages={messages} />
        </div>
      ) : (
        <div className="flex-1 w-full flex flex-col justify-center items-center">
          <WelcomeLayout />
          {chatBox}
        </div>
      )}

      {hasMessages && chatBox}

      {errorStage && <ErrorDialog stage={errorStage} onClose={clearError} />}
    </div>
  );
}
