import React, { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  BookOpen,
  Bot,
  BrainCircuit,
  Cpu,
  FileQuestion,
  FileText,
  HelpCircle,
  Image as ImageIcon,
  Loader2,
  MessageSquare,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
} from 'lucide-react';
import { chatService } from '../services/chatService';
import { documentService } from '../services/documentService';
import { multimodalService } from '../services/multimodalService';
import { ChatMessage as ChatMessageType, ChatSession } from '../types/chat';
import { DocumentItem } from '../types/documents';
import { ChatMessage } from '../components/chat/ChatMessage';
import { ChatInput } from '../components/chat/ChatInput';
import { ImageUploaderModal } from '../components/chat/ImageUploaderModal';
import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';

export const ChatPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedSessionId = searchParams.get('session');
  const requestedDocId = searchParams.get('doc');
  const requestedQuery = searchParams.get('query');
  const isNewRequested = searchParams.get('new') === '1';

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSession, setActiveSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [selectedImage, setSelectedImage] = useState<{ id: string; filename: string } | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isImageModalOpen, setIsImageModalOpen] = useState(false);
  const [isNewSessionModalOpen, setIsNewSessionModalOpen] = useState(false);
  const [newSessionSubject, setNewSessionSubject] = useState('Computer Science');
  const [newSessionTitle, setNewSessionTitle] = useState('');

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSending]);

  // Load user sessions and documents on mount
  useEffect(() => {
    const initializeChat = async () => {
      setIsLoading(true);
      try {
        const [loadedSessions, loadedDocs] = await Promise.all([
          chatService.listSessions().catch(() => []),
          documentService.listDocuments().catch(() => []),
        ]);

        setSessions(loadedSessions);
        setDocuments(loadedDocs);

        // Pre-select document if query param exists
        if (requestedDocId) {
          setSelectedDocIds([requestedDocId]);
        }

        // Determine active session
        if (isNewRequested || loadedSessions.length === 0) {
          // Auto create or prompt new session
          handleCreateSession('General Studies', 'Quick Study Session');
        } else if (requestedSessionId) {
          const match = loadedSessions.find((s) => s.id === requestedSessionId);
          if (match) {
            selectSession(match);
          } else {
            selectSession(loadedSessions[0]);
          }
        } else {
          selectSession(loadedSessions[0]);
        }
      } finally {
        setIsLoading(false);
      }
    };

    initializeChat();
  }, []);

  // Handle prefilled query param if present
  useEffect(() => {
    if (requestedQuery && activeSession && !isSending) {
      handleSendMessage({
        message: requestedQuery,
        intent: 'auto',
        difficulty: 'intermediate',
        llmProvider: 'gemini',
      });
      // Clear query param
      setSearchParams({ session: activeSession.id });
    }
  }, [requestedQuery, activeSession]);

  const selectSession = async (session: ChatSession) => {
    setActiveSession(session);
    setSearchParams({ session: session.id });
    try {
      const history = await chatService.getSessionMessages(session.id);
      setMessages(history);
      if (session.document_ids && session.document_ids.length > 0) {
        setSelectedDocIds(session.document_ids);
      }
    } catch (err) {
      console.error('Failed to load session messages:', err);
    }
  };

  const handleCreateSession = async (subject: string, title?: string) => {
    try {
      const newSession = await chatService.createSession(
        subject,
        title || subject,
        selectedDocIds
      );
      setSessions((prev) => [newSession, ...prev]);
      setActiveSession(newSession);
      setMessages([]);
      setSearchParams({ session: newSession.id });
      setIsNewSessionModalOpen(false);
      setNewSessionTitle('');
    } catch (err) {
      console.error('Failed to create session:', err);
    }
  };

  const handleSendMessage = async (params: {
    message: string;
    intent: 'auto' | 'tutor' | 'rag' | 'quiz' | 'summary' | 'learning_path';
    difficulty: 'beginner' | 'intermediate' | 'advanced';
    llmProvider: 'gemini' | 'ollama';
    imageId?: string;
  }) => {
    if (!activeSession) return;

    // Optimistically add user message
    const tempUserMsg: ChatMessageType = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: params.message,
      created_at: new Date().toISOString(),
      image_id: params.imageId,
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setIsSending(true);

    try {
      if (params.imageId) {
        // Mixed text + image query
        const mixedRes = await multimodalService.mixedQuery(
          params.message,
          params.imageId,
          selectedDocIds[0]
        );

        const assistantMsg: ChatMessageType = {
          id: `asst-${Date.now()}`,
          role: 'assistant',
          content: mixedRes.answer,
          created_at: new Date().toISOString(),
          agent_type: 'multimodal',
          model_used: params.llmProvider === 'gemini' ? 'Gemini Flash' : 'Ollama',
          citations: mixedRes.citations || [],
        };
        setMessages((prev) => [...prev, assistantMsg]);
        setSelectedImage(null);
      } else {
        // Progressive Server-Sent Events (SSE) Streaming
        const asstId = `asst-${Date.now()}`;
        const initialAsstMsg: ChatMessageType = {
          id: asstId,
          role: 'assistant',
          content: '',
          created_at: new Date().toISOString(),
          agent_type: params.intent,
          model_used: params.llmProvider === 'gemini' ? 'Gemini Flash' : 'Ollama',
          citations: [],
        };
        setMessages((prev) => [...prev, initialAsstMsg]);

        let accumulated = '';
        try {
          await chatService.streamMessage(
            {
              session_id: activeSession.id,
              content: params.message,
              intent: params.intent,
              difficulty: params.difficulty,
              document_ids: selectedDocIds,
              llm_override: params.llmProvider,
            },
            {
              onIntent: (data) => {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === asstId ? { ...m, agent_type: data.intent } : m
                  )
                );
              },
              onCitations: (citations) => {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === asstId ? { ...m, citations } : m
                  )
                );
              },
              onToken: (chunk) => {
                accumulated += chunk;
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === asstId ? { ...m, content: accumulated } : m
                  )
                );
              },
              onDone: (data) => {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === asstId ? { ...m, id: data.message_id || asstId } : m
                  )
                );
              },
              onError: (err) => {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === asstId ? { ...m, content: `⚠️ ${err}` } : m
                  )
                );
              },
            }
          );
        } catch (streamErr) {
          // Graceful fallback to standard REST request if streaming fails
          const response = await chatService.sendMessage({
            session_id: activeSession.id,
            content: params.message,
            intent: params.intent,
            difficulty: params.difficulty,
            document_ids: selectedDocIds,
            llm_override: params.llmProvider,
          });

          const asstData = response.assistant_message;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === asstId
                ? {
                    ...m,
                    id: asstData.id || asstId,
                    content: asstData.content,
                    agent_type: response.resolved_intent as any,
                    citations: asstData.sources || [],
                    quiz_data: asstData.quiz_data,
                    summary_data: asstData.summary_data,
                    recommendations: asstData.recommendations,
                  }
                : m
            )
          );
        }
      }
    } catch (err: any) {
      const errorMsg =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        'An error occurred while communicating with the AI Tutor. Please try again.';

      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `⚠️ **Error**: ${errorMsg}`,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const handleClearHistory = async () => {
    if (!activeSession) return;
    if (!window.confirm('Are you sure you want to clear chat messages in this session?')) return;
    try {
      await chatService.clearSessionMessages(activeSession.id);
      setMessages([]);
    } catch (err) {
      console.error('Failed to clear messages:', err);
    }
  };

  const promptSuggestions = [
    {
      title: 'ACID Transactions',
      query: 'Explain ACID properties in database management systems with intuitive real-world analogies.',
      icon: BrainCircuit,
    },
    {
      title: 'Algorithm Complexity',
      query: 'Derive and compare the time and space complexity of QuickSort vs MergeSort.',
      icon: Sparkles,
    },
    {
      title: 'Interactive Quiz',
      query: 'Generate a practice quiz with 4 MCQs on Computer Networks and OSI layer protocols.',
      icon: FileQuestion,
    },
    {
      title: 'Chapter Summary',
      query: 'Summarize the core concepts of process scheduling algorithms (FCFS, SJF, Round Robin).',
      icon: FileText,
    },
  ];

  return (
    <div className="h-[calc(100vh-8rem)] flex gap-6">
      {/* Session Drawer / Sidebar (Desktop) */}
      <div className="hidden md:flex flex-col w-72 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Study Sessions
          </h3>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setIsNewSessionModalOpen(true)}
            className="p-1.5 h-auto text-primary-600 dark:text-primary-400"
          >
            <Plus className="w-4 h-4" />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          {sessions.map((sess) => (
            <button
              key={sess.id}
              onClick={() => selectSession(sess)}
              className={`w-full text-left p-3 rounded-xl transition-all flex items-center gap-3 ${
                activeSession?.id === sess.id
                  ? 'bg-primary-50 dark:bg-primary-950/60 text-primary-900 dark:text-primary-100 font-semibold border border-primary-200 dark:border-primary-800'
                  : 'hover:bg-slate-50 dark:hover:bg-slate-800/50 text-slate-700 dark:text-slate-300'
              }`}
            >
              <MessageSquare className="w-4 h-4 text-primary-600 flex-shrink-0" />
              <div className="overflow-hidden">
                <p className="text-xs truncate">{sess.title}</p>
                <p className="text-[10px] text-slate-400 truncate">{sess.subject}</p>
              </div>
            </button>
          ))}
        </div>

        {/* Selected Document Filter in Session */}
        {documents.length > 0 && (
          <div className="p-3 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 text-xs">
            <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">
              Study Notes & Books
            </label>
            <select
              value={selectedDocIds[0] || ''}
              onChange={(e) => setSelectedDocIds(e.target.value ? [e.target.value] : [])}
              className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-xs text-slate-700 dark:text-slate-300 focus:outline-none"
            >
              <option value="">All Uploaded Materials</option>
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.original_filename}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Main Chat Conversation Container */}
      <div className="flex-1 flex flex-col bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl overflow-hidden shadow-sm">
        {/* Chat Header */}
        <div className="h-14 px-5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-lg bg-primary-50 dark:bg-primary-950/60 text-primary-600 dark:text-primary-400 flex items-center justify-center flex-shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div className="overflow-hidden">
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate">
                {activeSession?.title || 'Interactive AI Tutor'}
              </h2>
              <p className="text-[10px] text-slate-400">
                {activeSession?.subject || 'Multi-Agent Academic Assistant'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleClearHistory}
              title="Clear session messages"
              className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Message Thread Scroll Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto py-12">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-primary-600 to-indigo-500 text-white flex items-center justify-center mb-4 shadow-lg shadow-indigo-500/20">
                <BrainCircuit className="w-7 h-7" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-1">
                How can AisynEdu help you learn today?
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-8 max-w-sm">
                Ask a concept question, request a step-by-step mathematical derivation, or try one of the suggestions below:
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full text-left">
                {promptSuggestions.map((sug, i) => {
                  const Icon = sug.icon;
                  return (
                    <button
                      key={i}
                      onClick={() =>
                        handleSendMessage({
                          message: sug.query,
                          intent: 'auto',
                          difficulty: 'intermediate',
                          llmProvider: 'gemini',
                        })
                      }
                      className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 hover:border-primary-500 bg-slate-50/50 dark:bg-slate-800/40 text-left transition-all hover:shadow-sm"
                    >
                      <Icon className="w-4 h-4 text-primary-600 dark:text-primary-400 mb-2" />
                      <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                        {sug.title}
                      </p>
                      <p className="text-[11px] text-slate-400 line-clamp-2 mt-0.5">
                        {sug.query}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  onSelectTopic={(topic) =>
                    handleSendMessage({
                      message: `Explain ${topic} in detail with practical applications.`,
                      intent: 'auto',
                      difficulty: 'intermediate',
                      llmProvider: 'gemini',
                    })
                  }
                />
              ))}

              {isSending && (
                <div className="flex gap-3 items-center text-xs text-slate-400 italic py-2">
                  <Loader2 className="w-4 h-4 animate-spin text-primary-600" />
                  <span>AisynEdu is synthesizing explanation and citations...</span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Chat Input Bar */}
        <div className="p-4 border-t border-slate-100 dark:border-slate-800">
          <ChatInput
            onSend={handleSendMessage}
            isLoading={isSending}
            onOpenImageModal={() => setIsImageModalOpen(true)}
            selectedImage={selectedImage}
            onClearSelectedImage={() => setSelectedImage(null)}
          />
        </div>
      </div>

      {/* Multimodal Diagram Upload Modal */}
      <ImageUploaderModal
        isOpen={isImageModalOpen}
        onClose={() => setIsImageModalOpen(false)}
        onImageSelected={(img) => setSelectedImage(img)}
        onDirectExplain={(explanation, imgId) => {
          const directMsg: ChatMessageType = {
            id: `vision-${Date.now()}`,
            role: 'assistant',
            content: explanation,
            created_at: new Date().toISOString(),
            agent_type: 'multimodal',
            image_id: imgId,
          };
          setMessages((prev) => [...prev, directMsg]);
        }}
      />

      {/* New Session Creation Modal */}
      <Modal
        isOpen={isNewSessionModalOpen}
        onClose={() => setIsNewSessionModalOpen(false)}
        title="Start New Study Session"
        description="Organize your learning by subject or course topic."
        maxWidth="sm"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Subject Name
            </label>
            <input
              type="text"
              value={newSessionSubject}
              onChange={(e) => setNewSessionSubject(e.target.value)}
              placeholder="e.g. Computer Networks"
              className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Session Title (Optional)
            </label>
            <input
              type="text"
              value={newSessionTitle}
              onChange={(e) => setNewSessionTitle(e.target.value)}
              placeholder="e.g. Chapter 4: Transport Layer"
              className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <Button variant="outline" size="sm" onClick={() => setIsNewSessionModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleCreateSession(newSessionSubject, newSessionTitle)}
              disabled={!newSessionSubject.trim()}
            >
              Create Session
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

