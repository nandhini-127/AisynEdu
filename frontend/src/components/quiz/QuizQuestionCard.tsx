import React from 'react';
import { Check, CheckCircle2, HelpCircle, XCircle } from 'lucide-react';
import { QuizQuestion } from '../../types/quiz';

interface QuizQuestionCardProps {
  question: QuizQuestion;
  index: number;
  selectedOption?: number;
  onSelectOption: (optionIndex: number) => void;
  isSubmitted?: boolean;
}

export const QuizQuestionCard: React.FC<QuizQuestionCardProps> = ({
  question,
  index,
  selectedOption,
  onSelectOption,
  isSubmitted = false,
}) => {
  const letters = ['A', 'B', 'C', 'D'];
  const correct = question.correct_index ?? 0;

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl p-5 sm:p-6 shadow-sm">
      <div className="flex items-start justify-between gap-3 mb-4">
        <span className="text-xs font-bold px-2.5 py-1 rounded-lg bg-primary-50 dark:bg-primary-950/60 text-primary-700 dark:text-primary-300">
          Question {index + 1}
        </span>
        {isSubmitted && (
          <span
            className={`text-xs font-semibold px-2.5 py-1 rounded-lg flex items-center gap-1 ${
              selectedOption === correct
                ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300'
                : 'bg-red-50 dark:bg-red-950/60 text-red-700 dark:text-red-300'
            }`}
          >
            {selectedOption === correct ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5" /> Correct
              </>
            ) : (
              <>
                <XCircle className="w-3.5 h-3.5" /> Incorrect
              </>
            )}
          </span>
        )}
      </div>

      <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-5 leading-snug">
        {question.question}
      </h3>

      {/* Options */}
      <div className="space-y-2.5">
        {question.options.map((option, optIdx) => {
          const isSelected = selectedOption === optIdx;
          const isCorrect = correct === optIdx;

          let optionStyle =
            'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 bg-slate-50/50 dark:bg-slate-800/30 text-slate-800 dark:text-slate-200';

          if (isSubmitted) {
            if (isCorrect) {
              optionStyle =
                'border-emerald-500 bg-emerald-50 dark:bg-emerald-950/60 text-emerald-900 dark:text-emerald-100 font-semibold';
            } else if (isSelected && !isCorrect) {
              optionStyle =
                'border-red-500 bg-red-50 dark:bg-red-950/60 text-red-900 dark:text-red-100';
            } else {
              optionStyle = 'opacity-60 border-slate-200 dark:border-slate-800';
            }
          } else if (isSelected) {
            optionStyle =
              'border-primary-500 bg-primary-50/70 dark:bg-primary-950/60 text-primary-900 dark:text-primary-100 font-semibold ring-2 ring-primary-500/20';
          }

          return (
            <button
              key={optIdx}
              type="button"
              disabled={isSubmitted}
              onClick={() => onSelectOption(optIdx)}
              className={`w-full text-left p-3.5 rounded-xl border flex items-center justify-between transition-all ${optionStyle}`}
            >
              <div className="flex items-center gap-3">
                <span
                  className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${
                    isSelected
                      ? 'bg-primary-600 text-white'
                      : 'bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-600'
                  }`}
                >
                  {letters[optIdx]}
                </span>
                <span className="text-sm">{option}</span>
              </div>
              {isSubmitted && isCorrect && (
                <Check className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
              )}
            </button>
          );
        })}
      </div>

      {/* Explanation after submission */}
      {isSubmitted && question.explanation && (
        <div className="mt-4 p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-xs">
          <div className="flex items-center gap-1.5 font-bold text-slate-700 dark:text-slate-300 mb-1">
            <HelpCircle className="w-3.5 h-3.5 text-primary-600 dark:text-primary-400" />
            <span>Explanation & Concept Breakdown</span>
          </div>
          <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
            {question.explanation}
          </p>
        </div>
      )}
    </div>
  );
};

