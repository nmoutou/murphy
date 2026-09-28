'use client';

import { useEffect, useId, useRef } from 'react';
import type { ReactNode, SyntheticEvent } from 'react';

interface ModalProps {
  readonly title: string;
  /** Shown right of the title */
  readonly titleIcon?: ReactNode;
  readonly onClose: () => void;
  readonly children: ReactNode;
}

/**
 * A dialog over the page, whose background is greyed and inert (ADR-041). Mounted means
 * open: the parent decides when to show it, and hears Escape through `onClose`.
 */
/** Opens the native dialog on mount, closes it on unmount, and routes Escape to `onClose` */
function useModalDialog(onClose: () => void) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);

  const handleCancel = (event: SyntheticEvent<HTMLDialogElement>) => {
    event.preventDefault();
    onClose();
  };

  return { dialogRef, handleCancel };
}

export default function Modal({ title, titleIcon, onClose, children }: ModalProps) {
  const { dialogRef, handleCancel } = useModalDialog(onClose);
  const titleId = useId();

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      onCancel={handleCancel}
      className="m-auto w-[90%] max-w-md rounded-2xl bg-secondary p-6 text-tertiary backdrop:bg-black/60"
    >
      <div className="mb-4 flex items-center gap-3">
        {titleIcon}
        <h2 id={titleId} className="text-lg font-semibold">
          {title}
        </h2>
      </div>
      {children}
      <div className="mt-6 flex justify-end">
        <button
          type="button"
          onClick={onClose}
          className="rounded-full bg-quaternary px-4 py-1 text-secondary hover:opacity-80"
        >
          Fermer
        </button>
      </div>
    </dialog>
  );
}
