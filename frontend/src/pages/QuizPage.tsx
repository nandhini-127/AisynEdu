import React, { useEffect, useState } from 'react';
import {
  Award,
  BookOpen,
  CheckCircle2,
  FileQuestion,
  HelpCircle,
  History,
  Layers,
  Loader2,
  Play,
  RotateCcw,
  Sparkles,
} from 'lucide-react';
import { quizService } from '../services/quizService';
import { documentService } from '../services/documentService';
import { chatService } from '../services/chatService';
import { Quiz, QuizQuestion, QuizResult } from '../types/quiz';
import { DocumentItem } from '../types/documents';
import { ChatSession } from '../types/chat';
import { QuizQuestionCard } from '../components/quiz/QuizQuestionCard';
import { QuizResultView } from '../components/quiz/QuizResultView';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';

export const QuizPage: React.FC = () => {
  const [topic, setTopic] = useState('Operating Systems: Process Scheduling & Deadlocks');
  const [difficulty, setDifficulty] = useState<'beginner' | 'intermediate' | 'advanced'>('intermediate');
  const [questionCount, setQuestionCount] = useState(4);
  const [selectedDocId, setSelectedDocId] = useState<string>('');

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeQuiz, setActiveQuiz] = useState<Quiz | null>(null);
  const [userAnswers, setUserAnswers] = useState<Record<string, number>>({});
  const [quizResult, setQuizResult] = useState<QuizResult | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [quizHistory, setQuizHistory] = useState<any[]>([]);

  useEffect(() => {
    const loadResources = async () => {
      quizService.syncPendingQuizAttempts().catch(() => {});
      const [docs, sessList] = await Promise.all([
        documentService.listDocuments().catch(() => []),
        chatService.listSessions().catch(() => []),
      ]);
      setDocuments(docs);
      setSessions(sessList);
      setQuizHistory(quizService.getQuizHistory());
    };
    loadResources();
  }, []);

  const handleGenerateQuiz = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;

    setIsGenerating(true);
    setQuizResult(null);
    setUserAnswers({});

    try {
      // Find or create session for quiz generation
      let sessionId = sessions[0]?.id;
      if (!sessionId) {
        const createdSession = await chatService.createSession(
          'Quiz Generator',
          `Quiz: ${topic.slice(0, 30)}`
        );
        sessionId = createdSession.id;
        setSessions([createdSession]);
      }

      const generated = await quizService.generateQuiz({
        topic: topic.trim(),
        difficulty,
        sessionId,
        documentIds: selectedDocId ? [selectedDocId] : undefined,
        questionCount,
      });

      setActiveQuiz(generated);
    } catch (err: any) {
      console.error('Quiz generation error:', err);
      const detail = err?.response?.data?.detail || err?.response?.data?.message || err?.message;
      alert(detail ? `Quiz generation note: ${detail}` : 'Failed to generate quiz. Please check backend connection.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSelectOption = (questionId: string, optionIndex: number) => {
    setUserAnswers((prev) => ({
      ...prev,
      [questionId]: optionIndex,
    }));
  };

  const handleSubmitQuiz = async () => {
    if (!activeQuiz) return;
    const answeredCount = Object.keys(userAnswers).length;
    if (answeredCount < activeQuiz.questions.length) {
      if (!window.confirm(`You answered ${answeredCount} of ${activeQuiz.questions.length} questions. Submit anyway?`)) {
        return;
      }
    }

    const result = await quizService.submitQuiz({ quiz_id: activeQuiz.id, answers: userAnswers }, activeQuiz);
    setQuizResult(result);
    setQuizHistory(quizService.getQuizHistory());
  };

  const handleResetQuiz = () => {
    setUserAnswers({});
    setQuizResult(null);
  };

  return (
    <div className="space-y-8 pb-12 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
          <HelpCircle className="w-6 h-6 text-amber-500" />
          <span>Interactive Quiz Center</span>
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Generate customized MCQs from your course topics or uploaded textbooks to test conceptual mastery.
        </p>
      </div>

      {/* Generator Card (when no active quiz or want to create another) */}
      {!activeQuiz ? (
        <div className="space-y-6">
          <Card className="p-6 sm:p-8">
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-primary-600" />
              <span>Configure Practice Quiz</span>
            </h3>

            <form onSubmit={handleGenerateQuiz} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Quiz Topic or Chapter
                </label>
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g. Relational Database Normalization (1NF, 2NF, 3NF, BCNF)"
                  required
                  className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                    Difficulty Level
                  </label>
                  <select
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value as any)}
                    className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-700 dark:text-slate-300 focus:outline-none"
                  >
                    <option value="beginner">Beginner (Foundations)</option>
                    <option value="intermediate">Intermediate (Standard)</option>
                    <option value="advanced">Advanced (Deep Analysis)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                    Number of Questions
                  </label>
                  <select
                    value={questionCount}
                    onChange={(e) => setQuestionCount(Number(e.target.value))}
                    className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-700 dark:text-slate-300 focus:outline-none"
                  >
                    <option value={3}>3 Questions (Quick)</option>
                    <option value={4}>4 Questions (Balanced)</option>
                    <option value={5}>5 Questions (Comprehensive)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                    Study Notes / Book (Optional)
                  </label>
                  <select
                    value={selectedDocId}
                    onChange={(e) => setSelectedDocId(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-700 dark:text-slate-300 focus:outline-none"
                  >
                    <option value="">General Course Knowledge</option>
                    {documents.map((doc) => (
                      <option key={doc.id} value={doc.id}>
                        {doc.original_filename}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="pt-2">
                <Button
                  type="submit"
                  size="md"
                  isLoading={isGenerating}
                  leftIcon={<Play className="w-4 h-4" />}
                >
                  Generate Practice Quiz
                </Button>
              </div>
            </form>
          </Card>

          {/* Past Quiz History */}
          {quizHistory.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <History className="w-4 h-4 text-slate-400" />
                <span>Recent Quiz History</span>
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {quizHistory.slice(0, 4).map((item, idx) => (
                  <Card key={idx} className="p-4 flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate max-w-[200px]">
                        {item.title}
                      </p>
                      <p className="text-[10px] text-slate-400">
                        {item.score}/{item.total} correct •{' '}
                        {new Date(item.timestamp).toLocaleDateString()}
                      </p>
                    </div>
                    <Badge
                      variant={item.percentage >= 80 ? 'success' : item.percentage >= 60 ? 'warning' : 'danger'}
                      size="sm"
                    >
                      {item.percentage}%
                    </Badge>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Active Quiz Screen */
        <div className="space-y-6">
          {/* Quiz Top Action Bar */}
          <div className="flex items-center justify-between bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl p-4 shadow-sm">
            <div>
              <span className="text-xs font-semibold text-primary-600 dark:text-primary-400 uppercase tracking-wider">
                {activeQuiz.topic}
              </span>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                {activeQuiz.title}
              </h3>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setActiveQuiz(null);
                  setQuizResult(null);
                }}
              >
                Exit Quiz
              </Button>
            </div>
          </div>

          {/* Result view if submitted */}
          {quizResult ? (
            <div className="space-y-6">
              <QuizResultView
                result={quizResult}
                onRetake={handleResetQuiz}
                onBackToQuizzes={() => {
                  setActiveQuiz(null);
                  setQuizResult(null);
                }}
              />

              <div className="space-y-4">
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  Detailed Answer Explanations:
                </h3>
                {activeQuiz.questions.map((q, idx) => (
                  <QuizQuestionCard
                    key={q.id}
                    question={q}
                    index={idx}
                    selectedOption={userAnswers[q.id]}
                    onSelectOption={() => {}}
                    isSubmitted={true}
                  />
                ))}
              </div>
            </div>
          ) : (
            /* Questions in progress */
            <div className="space-y-5">
              {activeQuiz.questions.map((q, idx) => (
                <QuizQuestionCard
                  key={q.id}
                  question={q}
                  index={idx}
                  selectedOption={userAnswers[q.id]}
                  onSelectOption={(optIdx) => handleSelectOption(q.id, optIdx)}
                  isSubmitted={false}
                />
              ))}

              <div className="flex items-center justify-end pt-4">
                <Button
                  size="lg"
                  onClick={handleSubmitQuiz}
                  leftIcon={<CheckCircle2 className="w-5 h-5" />}
                >
                  Submit & Score Quiz
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

