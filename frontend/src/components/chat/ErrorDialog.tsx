'use client';

import Modal from '@/components/ui/Modal';
import AnimatedIcon from '@/components/icons/AnimatedIcon';
import type { DisplayedErrorStage } from '@/lib/chatErrorStage';

const ERROR_TITLE = 'Une erreur est survenue';
const RETRY_HINT = 'Vous pouvez reposer votre question dans un instant.';

const STAGE_MESSAGES: Record<DisplayedErrorStage, string> = {
  request: "Votre question n'a pas pu être traitée.",
  embedding: "L'encodage de votre question a échoué.",
  retrieval: 'La recherche des sources a échoué.',
  llm: 'La rédaction de la réponse a échoué.',
  internal: 'Une erreur interne est survenue.',
  connection: 'Le serveur est injoignable.',
};

interface ErrorDialogProps {
  readonly stage: DisplayedErrorStage;
  readonly onClose: () => void;
}

export default function ErrorDialog({ stage, onClose }: ErrorDialogProps) {
  const errorIcon = <AnimatedIcon icon="error" size={32} />;

  return (
    <Modal title={ERROR_TITLE} titleIcon={errorIcon} onClose={onClose}>
      <p>
        {STAGE_MESSAGES[stage]} {RETRY_HINT}
      </p>
    </Modal>
  );
}
