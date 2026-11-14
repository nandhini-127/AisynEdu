import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  BookOpen,
  Bot,
  Brain,
  CheckCircle2,
  Clock,
  FileQuestion,
  FileText,
  Flame,
  GraduationCap,
  HelpCircle,
  MessageSquare,
  Plus,
  Sparkles,
  TrendingUp,
  UploadCloud,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { chatService } from '../services/chatService';
import { documentService } from '../services/documentService';
import { quizService } from '../services/quizService';
import { analyticsService } from '../services/analyticsService';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { ChatSession } from '../types/chat';
import { DocumentItem } from '../types/documents';
import { DashboardAnalytics } from '../types/analytics';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [analytics, setAnalytics] = useState<DashboardAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [streakIncreasedBonus, setStreakIncreasedBonus] = useState(false);

  useEffect(() => {
    // Only show streak increase bonus/animation if backend confirmed it on login
    if (localStorage.getItem('edunex_streak_increased') === 'true') {
      setStreakIncreasedBonus(true);
      localStorage.removeItem('edunex_streak_increased');
      const timer = setTimeout(() => setStreakIncreasedBonus(false), 5000);
      return () => clearTimeout(timer);
    }
  }, []);

  const currentStreak = analytics?.current_streak ?? analytics?.study_streak_days ?? user?.current_streak ?? 0;
  const longestStreak = analytics?.longest_streak ?? user?.longest_streak ?? 0;
  const lastLoginInfo = analytics?.last_login_date ?? user?.last_login_date ?? null;

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        quizService.syncPendingQuizAttempts().catch(() => {});
        const [sessData, docsData, statsData] = await Promise.all([
          chatService.listSessions().catch(() => []),
          documentService.listDocuments().catch(() => []),
          analyticsService.getStudentAnalytics().catch(() => null),
        ]);
        setSessions(sessData);
        setDocuments(docsData);
        setAnalytics(statsData);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const statCards = [
    {
      label: 'Questions Explored',
      value: analytics?.total_questions_asked || 0,
      icon: MessageSquare,
      color: 'text-primary-600 dark:text-primary-400',
      bg: 'bg-primary-50 dark:bg-primary-950/60',
    },
    {
      label: 'Indexed Materials',
      value: documents.length,
      icon: BookOpen,
      color: 'text-indigo-600 dark:text-indigo-400',
      bg: 'bg-indigo-50 dark:bg-indigo-950/60',
    },
    {
      label: 'Quizzes Completed',
      value: Math.max(analytics?.total_quizzes_completed || 0, quizService.getQuizHistory().length || 0),
      icon: HelpCircle,
      color: 'text-amber-600 dark:text-amber-400',
      bg: 'bg-amber-50 dark:bg-amber-950/60',
    },
    {
      label: 'Login Streak',
      value: currentStreak === 0 ? '0 Days' : (currentStreak === 1 ? '1 Day' : `${currentStreak} Days`),
      subtitle: longestStreak > 0 ? `Best: ${longestStreak} ${longestStreak === 1 ? 'Day' : 'Days'}` : 'Log in tomorrow to build your streak!',
      icon: Flame,
      color: 'text-orange-500',
      bg: 'bg-orange-50 dark:bg-orange-950/60',
      highlight: streakIncreasedBonus,
    },
  ];

  return (
    <div className="space-y-8 pb-12">
      {/* Welcome Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-primary-900 via-primary-800 to-indigo-900 p-6 sm:p-8 text-white shadow-xl">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/10 backdrop-blur-md text-xs font-semibold text-primary-200 mb-3 border border-white/15">
            <Sparkles className="w-3.5 h-3.5 text-amber-300" />
            <span>Welcome back, {user?.name || 'Student'}!</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Ready to learn something new today?
          </h2>
          <p className="mt-2 text-sm text-primary-100 max-w-xl leading-relaxed">
            Your AisynEdu AI Tutor is ready with multi-agent concept explanations, multimodal diagram analysis, and instant practice quizzes.
          </p>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Button
              size="sm"
              variant="secondary"
              leftIcon={<Plus className="w-4 h-4 text-primary-700" />}
              onClick={() => navigate('/chat?new=1')}
            >
              Start New Chat
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="text-white border-white/20 hover:bg-white/10"
              leftIcon={<UploadCloud className="w-4 h-4" />}
              onClick={() => navigate('/documents')}
            >
              Upload Material
            </Button>
          </div>
        </div>

        {/* Decorative background glow */}
        <div className="absolute -right-10 -bottom-10 w-64 h-64 bg-primary-500/20 rounded-full blur-3xl pointer-events-none" />
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        {statCards.map((card, i) => {
          const Icon = card.icon;
          return (
            <Card key={i} hover className={`p-5 relative transition-all ${card.highlight ? 'ring-2 ring-orange-500 shadow-orange-500/20 shadow-lg animate-pulse' : ''}`}>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                  {card.label}
                </span>
                <div className={`w-8 h-8 rounded-xl ${card.bg} ${card.color} flex items-center justify-center`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div className="text-2xl font-extrabold text-slate-900 dark:text-slate-100 tracking-tight">
                {card.value}
              </div>
              {'subtitle' in card && card.subtitle && (
                <p className="text-[11px] text-slate-400 dark:text-slate-500 font-medium mt-1 truncate">
                  {card.subtitle}
                </p>
              )}
            </Card>
          );
        })}
      </div>

      {/* Main Grid: Recent Conversations & Uploaded Documents */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Conversations (2 cols) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                Recent Study Conversations
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Pick up where you left off with your AI Tutor
              </p>
            </div>
            <Link to="/chat" className="text-xs font-semibold text-primary-600 hover:text-primary-700 dark:text-primary-400 flex items-center gap-1">
              View All <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {sessions.length === 0 ? (
            <Card className="p-8 text-center">
              <Bot className="w-10 h-10 text-slate-400 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                No conversations yet
              </p>
              <p className="text-xs text-slate-400 mt-1 max-w-xs mx-auto mb-4">
                Start a session to explore academic concepts or ask questions about textbooks.
              </p>
              <Button size="sm" onClick={() => navigate('/chat?new=1')} leftIcon={<Plus className="w-4 h-4" />}>
                Create First Session
              </Button>
            </Card>
          ) : (
            <div className="space-y-3">
              {sessions.slice(0, 4).map((session) => (
                <div
                  key={session.id}
                  onClick={() => navigate(`/chat?session=${session.id}`)}
                  className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl p-4 flex items-center justify-between cursor-pointer hover:border-primary-500/40 hover:shadow-sm transition-all"
                >
                  <div className="flex items-center gap-3.5 overflow-hidden">
                    <div className="w-10 h-10 rounded-xl bg-primary-50 dark:bg-primary-950/60 text-primary-600 dark:text-primary-400 flex items-center justify-center flex-shrink-0">
                      <MessageSquare className="w-5 h-5" />
                    </div>
                    <div className="overflow-hidden">
                      <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">
                        {session.title}
                      </h4>
                      <p className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
                        <span className="text-primary-600 dark:text-primary-400 font-medium">{session.subject || 'General'}</span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {new Date(session.updated_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                        </span>
                      </p>
                    </div>
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate-400" />
                </div>
              ))}
            </div>
          )}

          {/* Recommended Next Topics */}
          {analytics?.recent_topics && (
            <div className="pt-2">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2.5">
                Suggested Review Topics
              </h4>
              <div className="flex flex-wrap gap-2">
                {analytics.recent_topics.map((topic, i) => (
                  <button
                    key={i}
                    onClick={() => navigate(`/chat?query=${encodeURIComponent(`Explain ${topic}`)}`)}
                    className="px-3 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs font-medium text-slate-700 dark:text-slate-300 hover:border-primary-500 hover:text-primary-600 transition-colors shadow-sm"
                  >
                    {topic}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Document Library & Quick Actions */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <Card className="p-5">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 mb-3">
              Quick Actions
            </h3>
            <div className="grid grid-cols-2 gap-2.5">
              <button
                onClick={() => navigate('/quiz')}
                className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 hover:bg-slate-100 dark:hover:bg-slate-800 text-left border border-slate-200 dark:border-slate-700 transition-colors"
              >
                <FileQuestion className="w-4 h-4 text-amber-500 mb-2" />
                <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                  Generate Quiz
                </p>
                <p className="text-[10px] text-slate-400">Test retention</p>
              </button>

              <button
                onClick={() => navigate('/notes')}
                className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 hover:bg-slate-100 dark:hover:bg-slate-800 text-left border border-slate-200 dark:border-slate-700 transition-colors"
              >
                <FileText className="w-4 h-4 text-purple-500 mb-2" />
                <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                  Study Notes
                </p>
                <p className="text-[10px] text-slate-400">Revision summaries</p>
              </button>
            </div>
          </Card>

          {/* Uploaded Materials Preview */}
          <Card className="p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Study Materials
              </h3>
              <Link to="/documents" className="text-xs font-semibold text-primary-600 hover:text-primary-700">
                Manage
              </Link>
            </div>

            {documents.length === 0 ? (
              <div className="text-center py-6">
                <BookOpen className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  No materials uploaded yet.
                </p>
                <Button
                  size="sm"
                  variant="outline"
                  className="mt-3"
                  onClick={() => navigate('/documents')}
                >
                  Upload First PDF
                </Button>
              </div>
            ) : (
              <div className="space-y-2.5">
                {documents.slice(0, 3).map((doc) => (
                  <div
                    key={doc.id}
                    className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-700/60 flex items-center justify-between"
                  >
                    <div className="overflow-hidden pr-2">
                      <p className="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate">
                        {doc.original_filename}
                      </p>
                      <p className="text-[10px] text-slate-400">
                        {doc.chunk_count} sections • {(doc.file_size_bytes / (1024 * 1024)).toFixed(1)} MB
                      </p>
                    </div>
                    <Badge variant={doc.status === 'ready' ? 'success' : 'warning'} size="sm">
                      {doc.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
};

