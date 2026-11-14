import React, { useEffect, useState } from 'react';
import {
  Award,
  BookOpen,
  Calendar,
  CheckCircle2,
  Flame,
  HelpCircle,
  MessageSquare,
  RefreshCw,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import { analyticsService } from '../services/analyticsService';
import { DashboardAnalytics } from '../types/analytics';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';

export const AnalyticsPage: React.FC = () => {
  const [data, setData] = useState<DashboardAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchAnalytics = async () => {
    setIsLoading(true);
    try {
      const res = await analyticsService.getStudentAnalytics();
      setData(res);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  return (
    <div className="space-y-8 pb-12 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            <TrendingUp className="w-6 h-6 text-primary-600" />
            <span>Learning Analytics & Progress Dashboard</span>
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Real-time telemetry on questions explored, quiz accuracy, and subject comprehension.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchAnalytics}
          leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
        >
          Refresh Data
        </Button>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Total Questions</span>
            <div className="w-8 h-8 rounded-xl bg-primary-50 dark:bg-primary-950/60 text-primary-600 flex items-center justify-center">
              <MessageSquare className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-slate-900 dark:text-slate-100">
            {data?.total_questions_asked || 0}
          </p>
          <p className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium mt-1">
            Active inquiry rate
          </p>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Uploaded Materials</span>
            <div className="w-8 h-8 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 flex items-center justify-center">
              <BookOpen className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-slate-900 dark:text-slate-100">
            {data?.total_documents_uploaded || 0}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">Indexed in ChromaDB</p>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Average Quiz Score</span>
            <div className="w-8 h-8 rounded-xl bg-amber-50 dark:bg-amber-950/60 text-amber-500 flex items-center justify-center">
              <Award className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-slate-900 dark:text-slate-100">
            {data?.average_quiz_score || 0}%
          </p>
          <p className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium mt-1">
            Strong concept mastery
          </p>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Login Streak</span>
            <div className="w-8 h-8 rounded-xl bg-orange-50 dark:bg-orange-950/60 text-orange-500 flex items-center justify-center">
              <Flame className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-slate-900 dark:text-slate-100">
            {(data?.current_streak ?? data?.study_streak_days ?? 0) === 1 ? '1 Day' : `${data?.current_streak ?? data?.study_streak_days ?? 0} Days`}
          </p>
          <p className="text-[11px] text-orange-500 font-medium mt-1">
            {(data?.longest_streak ?? 0) > 0 ? `Best streak: ${data?.longest_streak} ${(data?.longest_streak ?? 0) === 1 ? 'Day' : 'Days'}` : 'Consistent learning'}
          </p>
        </Card>
      </div>

      {/* Charts Section: Weekly Activity & Subject Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Weekly Activity (2 cols) */}
        <Card className="lg:col-span-2 p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Weekly Learning Activity
              </h3>
              <p className="text-xs text-slate-400">Number of queries and quizzes answered per day</p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5 text-slate-600 dark:text-slate-400">
                <span className="w-2.5 h-2.5 rounded-full bg-primary-600 inline-block" /> Queries
              </span>
              <span className="flex items-center gap-1.5 text-slate-600 dark:text-slate-400">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" /> Quizzes
              </span>
            </div>
          </div>

          {/* Bar Chart Visualization */}
          <div className="h-64 flex items-end justify-between gap-2 sm:gap-4 pt-4 border-b border-slate-200 dark:border-slate-800">
            {data?.daily_activity.map((item, idx) => {
              const queryHeight = Math.min(Math.max((item.queries_count / 15) * 100, 15), 90);
              const quizHeight = Math.min(Math.max((item.quizzes_count / 3) * 100, 10), 80);

              return (
                <div key={idx} className="flex-1 flex flex-col items-center gap-1 h-full justify-end">
                  <div className="w-full flex items-end justify-center gap-1.5 h-48">
                    {/* Queries bar */}
                    <div
                      className="w-1/2 max-w-[20px] bg-primary-600 dark:bg-primary-500 rounded-t-lg transition-all duration-300 hover:opacity-90 relative group"
                      style={{ height: `${queryHeight}%` }}
                    >
                      <div className="opacity-0 group-hover:opacity-100 absolute -top-7 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-[10px] py-0.5 px-1.5 rounded pointer-events-none transition-opacity">
                        {item.queries_count}
                      </div>
                    </div>
                    {/* Quizzes bar */}
                    <div
                      className="w-1/2 max-w-[20px] bg-amber-500 dark:bg-amber-400 rounded-t-lg transition-all duration-300 hover:opacity-90 relative group"
                      style={{ height: `${quizHeight}%` }}
                    >
                      <div className="opacity-0 group-hover:opacity-100 absolute -top-7 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-[10px] py-0.5 px-1.5 rounded pointer-events-none transition-opacity">
                        {item.quizzes_count}
                      </div>
                    </div>
                  </div>
                  <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 mt-2">
                    {item.date}
                  </span>
                </div>
              );
            })}
          </div>
        </Card>

        {/* Subject Breakdown (1 col) */}
        <Card className="p-6">
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 mb-1">
            Subject Focus Breakdown
          </h3>
          <p className="text-xs text-slate-400 mb-6">Distribution across academic topics</p>

          <div className="space-y-4">
            {data?.subject_breakdown.map((sub, idx) => (
              <div key={idx} className="space-y-1.5">
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span className="text-slate-800 dark:text-slate-200">{sub.subject}</span>
                  <span className="text-primary-600 dark:text-primary-400">{sub.percentage}%</span>
                </div>
                <div className="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary-600 rounded-full transition-all duration-500"
                    style={{ width: `${sub.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-8 p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-xs text-slate-600 dark:text-slate-400">
            <span className="font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-1.5 mb-1">
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              Insight:
            </span>
            You are spending most of your study sessions in {data?.subject_breakdown[0]?.subject || 'Computer Science'}. Consider reviewing {data?.subject_breakdown[data?.subject_breakdown.length - 1]?.subject || 'Mathematics'} for balanced preparation.
          </div>
        </Card>
      </div>
    </div>
  );
};

