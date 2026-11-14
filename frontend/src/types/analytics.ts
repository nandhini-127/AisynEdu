export interface DashboardAnalytics {
  total_questions_asked: number;
  total_documents_uploaded: number;
  total_quizzes_completed: number;
  average_quiz_score: number;
  study_streak_days: number;
  current_streak?: number;
  longest_streak?: number;
  last_login_date?: string | null;
  last_login?: string | null;
  daily_activity: {
    date: string;
    queries_count: number;
    quizzes_count: number;
  }[];
  subject_breakdown: {
    subject: string;
    percentage: number;
    count: number;
  }[];
  recent_topics: string[];
}

