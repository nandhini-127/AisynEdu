import React from 'react';
import { BookOpen } from 'lucide-react';
import { Citation } from '../../types/chat';

interface CitationBadgeProps {
  citation: Citation;
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({ citation }) => {
  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors border border-slate-200 dark:border-slate-700">
      <BookOpen className="w-3.5 h-3.5 text-primary-600 dark:text-primary-400" />
      <span className="font-semibold truncate max-w-[150px]">
        {citation.document_name}
      </span>
      {citation.page_number && (
        <span className="text-slate-400 dark:text-slate-500 font-mono">
          p. {citation.page_number}
        </span>
      )}
    </div>
  );
};

