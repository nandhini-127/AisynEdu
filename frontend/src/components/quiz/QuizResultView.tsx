import React, { useEffect } from 'react';
import confetti from 'canvas-confetti';
import { Award, CheckCircle2, RotateCcw, Trophy, XCircle } from 'lucide-react';
import { QuizResult } from '../../types/quiz';
import { Button } from '../common/Button';

interface QuizResultViewProps {
  result: QuizResult;
  onRetake: () => void;
  onBackToQuizzes: () => void;
}

export const QuizResultView: React.FC<QuizResultViewProps> = ({
  result,
  onRetake,
  onBackToQuizzes,
}) => {
  useEffect(() => {
    if (result.percentage >= 70) {
      confetti({
        particleCount: 80,
        spread: 70,
        origin: { y: 0.6 },
      });
    }
  }, [result.percentage]);

  const getScoreColor = () => {
    if (result.percentage >= 80) return 'text-emerald-600 dark:text-emerald-400';
    if (result.percentage >= 60) return 'text-amber-600 dark:text-amber-400';
    return 'text-red-600 dark:text-red-400';
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl p-6 sm:p-8 text-center max-w-xl mx-auto shadow-sm">
      <div className="w-16 h-16 rounded-2xl bg-amber-50 dark:bg-amber-950/50 text-amber-500 flex items-center justify-center mx-auto mb-4 shadow-sm">
        <Trophy className="w-8 h-8" />
      </div>

      <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 mb-1">
        Quiz Completed!
      </h2>
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-6">
        Here is your performance summary and concept mastery rating.
      </p>

      {/* Score circle / card */}
      <div className="p-6 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 mb-6">
        <div className={`text-4xl font-extrabold ${getScoreColor()}`}>
          {result.percentage}%
        </div>
        <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mt-1">
          {result.score} out of {result.total_questions} correct
        </p>

        {/* Progress bar */}
        <div className="w-full bg-slate-200 dark:bg-slate-700 h-2.5 rounded-full mt-4 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              result.percentage >= 80
                ? 'bg-emerald-500'
                : result.percentage >= 60
                ? 'bg-amber-500'
                : 'bg-red-500'
            }`}
            style={{ width: `${result.percentage}%` }}
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-center gap-3">
        <Button variant="outline" onClick={onRetake} leftIcon={<RotateCcw className="w-4 h-4" />}>
          Retake Quiz
        </Button>
        <Button variant="primary" onClick={onBackToQuizzes} leftIcon={<Award className="w-4 h-4" />}>
          Back to Quiz Center
        </Button>
      </div>
    </div>
  );
};

