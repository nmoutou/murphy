'use client';

import Modal from '@/components/ui/Modal';
import AnimatedIcon from '@/components/icons/AnimatedIcon';
import { useErrorStore } from '@/stores/errorStore';
import { ERROR_MESSAGES } from './errorMessages';

const ERROR_TITLE = 'Une erreur est survenue';
const ERROR_ICON_SIZE = 32;

/** La seule modale d'erreur : la recherche comme les documents la nourrissent par le store */
export default function ErrorDialog() {
  const errorCode = useErrorStore((state) => state.errorCode);
  const clearError = useErrorStore((state) => state.clearError);

  if (!errorCode) return null;

  const errorIcon = <AnimatedIcon icon="error" size={ERROR_ICON_SIZE} />;
  return (
    <Modal title={ERROR_TITLE} titleIcon={errorIcon} onClose={clearError}>
      <p>{ERROR_MESSAGES[errorCode]}</p>
    </Modal>
  );
}
