import React, { useEffect, useState } from 'react';
import {
  BookOpen,
  CheckCircle,
  Clock,
  FileText,
  Filter,
  HardDrive,
  Layers,
  Plus,
  RefreshCw,
  Search,
  UploadCloud,
} from 'lucide-react';
import { documentService } from '../services/documentService';
import { DocumentItem } from '../types/documents';
import { DocumentListItem } from '../components/documents/DocumentListItem';
import { DocumentUploadModal } from '../components/documents/DocumentUploadModal';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { EmptyState } from '../components/common/EmptyState';

export const DocumentsPage: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [subjectFilter, setSubjectFilter] = useState('all');
  const [isLoading, setIsLoading] = useState(true);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  const fetchDocuments = async () => {
    setIsLoading(true);
    try {
      const docs = await documentService.listDocuments();
      setDocuments(docs);
    } catch (err) {
      console.error('Failed to fetch documents:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleDeleteDocument = async (id: string) => {
    try {
      await documentService.deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      console.error('Failed to delete document:', err);
      alert('Could not delete document. Please try again.');
    }
  };

  const handleDocumentUploaded = (newDoc: DocumentItem) => {
    setDocuments((prev) => [newDoc, ...prev]);
  };

  // Unique subjects for filter
  const subjects = Array.from(
    new Set(documents.map((d) => d.subject).filter(Boolean) as string[])
  );

  const filteredDocuments = documents.filter((doc) => {
    const matchesSearch =
      doc.original_filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (doc.subject && doc.subject.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesSubject =
      subjectFilter === 'all' || doc.subject === subjectFilter;

    return matchesSearch && matchesSubject;
  });

  const totalChunks = documents.reduce((acc, d) => acc + (d.chunk_count || 0), 0);
  const totalMB = (
    documents.reduce((acc, d) => acc + (d.file_size_bytes || 0), 0) /
    (1024 * 1024)
  ).toFixed(1);

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Document Library
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Manage your indexed study materials, textbooks, and course lecture notes.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchDocuments}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setIsUploadModalOpen(true)}
            leftIcon={<UploadCloud className="w-4 h-4" />}
          >
            Upload Material
          </Button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="p-4 flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-primary-50 dark:bg-primary-950/60 text-primary-600 flex items-center justify-center">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400">Total Materials</p>
            <p className="text-xl font-bold text-slate-900 dark:text-slate-100">{documents.length}</p>
          </div>
        </Card>

        <Card className="p-4 flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 flex items-center justify-center">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400">Indexed Study Sections</p>
            <p className="text-xl font-bold text-slate-900 dark:text-slate-100">{totalChunks}</p>
          </div>
        </Card>

        <Card className="p-4 flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 flex items-center justify-center">
            <HardDrive className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400">Storage Used</p>
            <p className="text-xl font-bold text-slate-900 dark:text-slate-100">{totalMB} MB</p>
          </div>
        </Card>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl p-3 shadow-sm">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search documents by name or subject..."
            className="w-full pl-9 pr-4 py-2 rounded-xl text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
          />
        </div>

        {subjects.length > 0 && (
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <Filter className="w-4 h-4 text-slate-400 flex-shrink-0" />
            <select
              value={subjectFilter}
              onChange={(e) => setSubjectFilter(e.target.value)}
              className="w-full sm:w-auto px-3 py-2 rounded-xl text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 focus:outline-none"
            >
              <option value="all">All Subjects</option>
              {subjects.map((sub) => (
                <option key={sub} value={sub}>
                  {sub}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Document List */}
      {isLoading ? (
        <div className="py-16 text-center text-slate-400 text-xs">
          Loading document library...
        </div>
      ) : filteredDocuments.length === 0 ? (
        <EmptyState
          icon={<BookOpen className="w-7 h-7" />}
          title={searchQuery ? 'No matching documents found' : 'No study materials uploaded'}
          description={
            searchQuery
              ? 'Try modifying your search term or clear the filter.'
              : 'Upload course PDFs to allow the AI Tutor to answer questions citing your textbook pages.'
          }
          actionText="Upload Study Material"
          actionIcon={<Plus className="w-4 h-4" />}
          onAction={() => setIsUploadModalOpen(true)}
        />
      ) : (
        <div className="space-y-3">
          {filteredDocuments.map((doc) => (
            <DocumentListItem
              key={doc.id}
              document={doc}
              onDelete={handleDeleteDocument}
            />
          ))}
        </div>
      )}

      {/* Upload Modal */}
      <DocumentUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploaded={handleDocumentUploaded}
      />
    </div>
  );
};

