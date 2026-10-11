import type { DocumentType } from '@murphy/contract/search';
import Icon from '@/components/icons/Icon';
import { describeDocumentType } from '@/lib/documentTypeLabels';
import { selectDocumentIcon } from './documentIcons';

const DOCUMENT_ICON_SIZE = 20;

interface DocumentIconProps {
  readonly documentType: DocumentType;
  readonly nature?: string;
}

/** L'icône seule ne dit pas le type : son nom accessible et son infobulle le disent */
export default function DocumentIcon({ documentType, nature }: DocumentIconProps) {
  const description = describeDocumentType(documentType, nature);

  return (
    <span role="img" aria-label={description} title={description} className="shrink-0">
      <Icon icon={selectDocumentIcon(documentType, nature)} size={DOCUMENT_ICON_SIZE} />
    </span>
  );
}
