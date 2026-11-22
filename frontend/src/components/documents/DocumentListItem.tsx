import React, { useState } from 'react';
import {
  BookOpen,
  Calendar,
  CheckCircle,
  Clock,
  FileText,
  HardDrive,
  Layers,
  MessageSquare,
  Trash2,
  XCircle,
} from 'lucide-react';
import { DocumentItem } from '../../types/documents';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { useNavigate } from 'react-router-dom';

interface DocumentListItemProps {
  document: DocumentItem;
  onDelete: (id: string) => void;
}

export const DocumentListItem: React.FC<DocumentListItemProps> = ({ document, onDelete }) => {
  const [isDeleting, setIsDeleting] = useState(false);
  const navigate = useNavigate();

  const handleDelete = async () => {
    const filename = document?.original_filename || 'this document';
    if (!document?.id) return;
    if (!window.confirm(`Are you sure you want to delete "${filename}"?`)) return;
    setIsDeleting(true);
    try {
      await onDelete(document.id);
    } finally {
      setIsDeleting(false);
    }
  };

  const getStatusBadge = () => {
    switch (document?.status) {
      case 'ready':
        return (
          <Badge variant="success" size="sm" className="gap-1">
            <CheckCircle className="w-3 h-3" /> Ready
          </Badge>
        );
      case 'processing':
        return (
          <Badge variant="warning" size="sm" className="gap-1">
            <Clock className="w-3 h-3" /> Processing
          </Badge>
        );
      case 'failed':
        return (
          <Badge variant="danger" size="sm" className="gap-1">
            <XCircle className="w-3 h-3" /> Failed
          </Badge>
        );
      default:
        return <Badge size="sm">{document?.status || 'ready'}</Badge>;
    }
  };

  const filename = document?.original_filename || 'Untitled Document';
  const sizeBytes = document?.file_size_bytes || 0;
  const formattedSize = (sizeBytes / (1024 * 1024)).toFixed(2);
  const formattedDate = document?.created_at
    ? new Date(document.created_at).toLocaleDateString([], {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    : 'Recently';

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all hover:shadow-sm">
      <div className="flex items-start gap-3.5 overflow-hidden">
        <div className="w-10 h-10 rounded-xl bg-red-50 dark:bg-red-950/50 text-red-600 dark:text-red-400 flex items-center justify-center flex-shrink-0 border border-red-200 dark:border-red-900/50">
          <FileText className="w-5 h-5" />
        </div>
        <div className="overflow-hidden">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">
              {filename}
            </h4>
            {getStatusBadge()}
          </div>
          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
            {document?.subject && (
              <span className="font-medium text-primary-600 dark:text-primary-400">
                {document.subject}
              </span>
            )}
            <span className="flex items-center gap-1">
              <HardDrive className="w-3 h-3" /> {formattedSize} MB
            </span>
            <span className="flex items-center gap-1">
              <Layers className="w-3 h-3" /> {document?.chunk_count || 0} Sections
            </span>
            <span className="flex items-center gap-1">
              <Calendar className="w-3 h-3" /> {formattedDate}
            </span>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 self-end sm:self-center">
        <Button
          size="sm"
          variant="outline"
          leftIcon={<MessageSquare className="w-3.5 h-3.5" />}
          onClick={() => navigate(`/chat?doc=${document.id}`)}
          disabled={document.status !== 'ready'}
        >
          Ask Tutor
        </Button>
        <button
          onClick={handleDelete}
          disabled={isDeleting}
          className="p-2 rounded-xl text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors"
          title="Delete study material"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

