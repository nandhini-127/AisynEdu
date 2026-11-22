import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import {
  BookOpen,
  Bookmark,
  Check,
  Copy,
  Download,
  FileText,
  Lightbulb,
  Loader2,
  Plus,
  Sparkles,
  Trash2,
} from 'lucide-react';
import { chatService } from '../services/chatService';
import { documentService } from '../services/documentService';
import { notesService, SavedNote } from '../services/notesService';
import { useAuth } from '../context/AuthContext';
import { DocumentItem } from '../types/documents';
import { ChatSession } from '../types/chat';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';

export const StudyNotesPage: React.FC = () => {
  const { user } = useAuth();
  const [subject, setSubject] = useState('Computer Science');
  const [topic, setTopic] = useState('Database Indexing: B-Trees vs Hash Indexes');
  const [selectedDocId, setSelectedDocId] = useState('');
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentNote, setCurrentNote] = useState<SavedNote | null>(null);
  const [savedNotes, setSavedNotes] = useState<SavedNote[]>([]);
  const [copied, setCopied] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const init = async () => {
      const [docs, sessList] = await Promise.all([
        documentService.listDocuments().catch(() => []),
        chatService.listSessions().catch(() => []),
      ]);
      if (!isMounted) return;
      setDocuments(docs);
      setSessions(sessList);

      // Load saved notes for current authenticated user
      try {
        const userNotes = await notesService.listNotes(user?.id);
        if (!isMounted) return;
        setSavedNotes(userNotes);
        if (userNotes.length > 0) {
          setCurrentNote(userNotes[0]);
        } else {
          setCurrentNote(null);
        }
      } catch (e) {
        if (!isMounted) return;
        const cached = notesService.getCachedNotes(user?.id);
        setSavedNotes(cached);
        if (cached.length > 0) {
          setCurrentNote(cached[0]);
        } else {
          setCurrentNote(null);
        }
      }
    };
    init();
    return () => {
      isMounted = false;
    };
  }, [user?.id]);

  const handleGenerateSummary = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;

    setIsGenerating(true);
    try {
      let sessionId = sessions[0]?.id;
      if (!sessionId) {
        const sess = await chatService.createSession(subject, `Notes: ${topic}`);
        sessionId = sess.id;
        setSessions([sess]);
      }

      const prompt = `Generate structured, high-yield study revision notes for: "${topic}".
Include:
1. **Core Concept & Fundamental Definitions**: Clear academic summary.
2. **Key Architectural Blocks / Step-by-Step Mechanisms**: Highlight operational details.
3. **Important Mathematical Equations / Complexity Formulas**: Include LaTeX notation ($...$).
4. **Exam Takeaways & Common Pitfalls**: 3 to 4 crucial points students should remember for exams.`;

      const res = await chatService.sendMessage({
        session_id: sessionId,
        content: prompt,
        intent: 'summarize',
        document_ids: selectedDocId ? [selectedDocId] : undefined,
      });

      const noteContent = res.assistant_message?.content || 'No summary content generated.';
      const newNote = await notesService.createNote(
        {
          title: topic,
          subject,
          content: noteContent,
          document_id: selectedDocId || undefined,
        },
        user?.id
      );

      setCurrentNote(newNote);
      setSavedNotes((prev) => [newNote, ...prev.filter((n) => n.id !== newNote.id)]);
    } catch (err) {
      console.error('Failed to generate summary notes:', err);
      alert('Could not generate notes. Please verify backend connection.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopyNote = () => {
    if (!currentNote) return;
    navigator.clipboard.writeText(currentNote.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDeleteNote = async (id: string) => {
    await notesService.deleteNote(id, user?.id);
    const updated = savedNotes.filter((n) => n.id !== id);
    setSavedNotes(updated);
    if (currentNote?.id === id) {
      setCurrentNote(updated[0] || null);
    }
  };

  const handleDownloadPDF = async () => {
    if (!currentNote || !currentNote.content.trim()) return;

    setIsExportingPdf(true);
    try {
      const blob = await chatService.exportNotesPDF({
        title: currentNote.title,
        subject: currentNote.subject,
        content: currentNote.content,
      });

      if (!blob || blob.size === 0) {
        throw new Error('Received empty PDF document from server.');
      }

      // Create download URL with application/pdf MIME type
      const pdfBlob = new Blob([blob], { type: 'application/pdf' });
      const url = URL.createObjectURL(pdfBlob);
      const link = document.createElement('a');
      link.href = url;
      const safeTitle = currentNote.title.replace(/[^\w\s-]/g, '').trim().replace(/[-\s]+/g, '_') || 'study_notes';
      link.download = `${safeTitle}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      console.error('Failed to download PDF:', err);
      const msg = err?.response?.data?.detail || err?.message || 'Could not generate PDF. Please try again.';
      alert(`PDF Export Error: ${msg}`);
    } finally {
      setIsExportingPdf(false);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
          <FileText className="w-6 h-6 text-purple-600" />
          <span>Automated Study Summaries & Revision Notes</span>
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Synthesize key definitions, formulas, and high-yield exam takeaways from your materials.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Generator Form & Saved Notes List */}
        <div className="space-y-6">
          <Card className="p-5">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 mb-3 flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-purple-600" />
              <span>Generate New Notes</span>
            </h3>

            <form onSubmit={handleGenerateSummary} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Subject
                </label>
                <input
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="e.g. Operating Systems"
                  required
                  className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Concept or Chapter Topic
                </label>
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g. TCP Handshake and Congestion Control"
                  required
                  className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none"
                />
              </div>

              {documents.length > 0 && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Grounding Material
                  </label>
                  <select
                    value={selectedDocId}
                    onChange={(e) => setSelectedDocId(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-700 dark:text-slate-300 focus:outline-none"
                  >
                    <option value="">General Course Material</option>
                    {documents.map((doc) => (
                      <option key={doc.id} value={doc.id}>
                        {doc.original_filename}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <Button
                type="submit"
                size="sm"
                className="w-full"
                isLoading={isGenerating}
                leftIcon={<Sparkles className="w-3.5 h-3.5" />}
              >
                Synthesize Revision Notes
              </Button>
            </form>
          </Card>

          {/* Saved Notes Index */}
          <Card className="p-5">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 mb-3 flex items-center justify-between">
              <span>Saved Revision Notes</span>
              <span className="text-xs font-normal text-slate-400">({savedNotes.length})</span>
            </h3>

            {savedNotes.length === 0 ? (
              <p className="text-xs text-slate-400 text-center py-6">
                No saved notes yet. Generate your first revision summary above!
              </p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                {savedNotes.map((note) => (
                  <div
                    key={note.id}
                    onClick={() => setCurrentNote(note)}
                    className={`p-3 rounded-xl border text-xs cursor-pointer transition-all flex items-center justify-between ${
                      currentNote?.id === note.id
                        ? 'border-purple-500 bg-purple-50/70 dark:bg-purple-950/60 font-semibold'
                        : 'border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50'
                    }`}
                  >
                    <div className="overflow-hidden pr-2">
                      <p className="truncate text-slate-800 dark:text-slate-200">{note.title}</p>
                      <p className="text-[10px] text-slate-400">{note.subject}</p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteNote(note.id);
                      }}
                      className="p-1 text-slate-400 hover:text-red-500"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Right Column (2 cols): Note Viewer / Reader */}
        <div className="lg:col-span-2">
          {currentNote ? (
            <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-6">
              {/* Note Header & Action Buttons */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100 dark:border-slate-800">
                <div>
                  <Badge variant="purple" size="sm" className="mb-1.5">
                    {currentNote.subject}
                  </Badge>
                  <h3 className="text-xl font-bold text-slate-900 dark:text-white">
                    {currentNote.title}
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Generated on {new Date(currentNote.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleCopyNote}
                    leftIcon={copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                  >
                    {copied ? 'Copied' : 'Copy'}
                  </Button>
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={handleDownloadPDF}
                    isLoading={isExportingPdf}
                    disabled={isExportingPdf}
                    leftIcon={<Download className="w-3.5 h-3.5" />}
                  >
                    {isExportingPdf ? 'Generating PDF...' : 'Download PDF'}
                  </Button>
                </div>
              </div>

              {/* Rendered Markdown Note Body */}
              <div className="prose dark:prose-invert prose-sm max-w-none prose-headings:font-bold prose-headings:text-slate-900 dark:prose-headings:text-slate-100 prose-pre:bg-slate-950 prose-pre:border prose-pre:border-slate-800 leading-relaxed">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkMath]}
                  rehypePlugins={[rehypeKatex]}
                >
                  {currentNote.content}
                </ReactMarkdown>
              </div>
            </div>
          ) : (
            <Card className="p-12 text-center">
              <FileText className="w-12 h-12 text-slate-400 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-slate-800 dark:text-slate-200">
                No note selected
              </h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1">
                Configure a study topic on the left to synthesize structured notes with LaTeX equations and key exam takeaways.
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

