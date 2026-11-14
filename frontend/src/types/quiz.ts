export interface QuizQuestion {
  id: string;
  question: string;
  options: string[];
  explanation: string;
  correct_index?: number; // Only returned on review/after submission
}

export interface Quiz {
  id: string;
  title: string;
  topic: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  questions: QuizQuestion[];
  created_at: string;
}

export interface QuizSubmission {
  quiz_id: string;
  answers: Record<string, number>; // question_id -> selected_option_index
}

export interface QuizResult {
  score: number;
  total_questions: number;
  percentage: number;
  details: {
    question_id: string;
    question: string;
    selected_index: number;
    correct_index: number;
    is_correct: boolean;
    explanation: string;
  }[];
}

