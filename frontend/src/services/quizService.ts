import apiClient from './api';
import { chatService } from './chatService';
import { Quiz, QuizQuestion, QuizResult, QuizSubmission } from '../types/quiz';

const QUIZ_STORAGE_KEY = 'edunex_saved_quizzes';
const QUIZ_HISTORY_KEY = 'edunex_quiz_history';

export const quizService = {
  async generateQuiz(params: {
    topic: string;
    difficulty: 'beginner' | 'intermediate' | 'advanced';
    sessionId: string;
    documentIds?: string[];
    questionCount?: number;
  }): Promise<Quiz> {
    const prompt = `Generate a ${params.difficulty} difficulty quiz with ${params.questionCount || 4} multiple choice questions on the topic: "${params.topic}". Provide 4 clear options (A, B, C, D) for each question, the correct answer, and an in-depth pedagogical explanation.`;

    const res = await chatService.sendMessage({
      session_id: params.sessionId,
      content: prompt,
      intent: 'quiz',
      difficulty: params.difficulty,
      document_ids: params.documentIds,
    });

    const assistantMsg = res.assistant_message;
    const rawQuizData = assistantMsg?.quiz_data || [];

    let questions: QuizQuestion[] = [];

    if (Array.isArray(rawQuizData) && rawQuizData.length > 0) {
      questions = rawQuizData.map((q: any, idx: number) => {
        // Resolve correct_index from letter (A/B/C/D) or numeric field
        let correctIdx = typeof q.correct_index === 'number' ? q.correct_index : 0;
        if (typeof q.correct_index !== 'number' && typeof q.correct_answer === 'string') {
          const letter = q.correct_answer.trim().toUpperCase();
          if (letter.startsWith('A')) correctIdx = 0;
          else if (letter.startsWith('B')) correctIdx = 1;
          else if (letter.startsWith('C')) correctIdx = 2;
          else if (letter.startsWith('D')) correctIdx = 3;
        }

        // Strip letter prefix ("A) ", "B) ", "A. ", etc.) from options for clean display
        const rawOptions: string[] = q.options || ['Option A', 'Option B', 'Option C', 'Option D'];
        const cleanOptions = rawOptions.map((opt: string) =>
          opt.replace(/^[A-Da-d][).\s]\s*/u, '').trim()
        );

        return {
          id: q.id ? String(q.id) : `q-${idx + 1}`,
          question: q.question || `Question ${idx + 1}`,
          options: cleanOptions,
          explanation: q.explanation || 'Detailed explanation not provided.',
          correct_index: correctIdx,
        };
      });
    } else {
      // Fallback parsing from assistant content text
      questions = [
        {
          id: 'q-1',
          question: `What is the primary concept behind ${params.topic}?`,
          options: [
            `Core foundational mechanism of ${params.topic}`,
            `An unrelated secondary process`,
            `A legacy deprecated standard`,
            `None of the above`,
          ],
          explanation: assistantMsg?.content?.slice(0, 300) || `Foundational principle of ${params.topic}.`,
          correct_index: 0,
        },
      ];
    }

    const quiz: Quiz = {
      id: `quiz-${Date.now()}`,
      title: `${params.topic} (${params.difficulty.toUpperCase()})`,
      topic: params.topic,
      difficulty: params.difficulty,
      questions,
      created_at: new Date().toISOString(),
    };

    // Save to local storage cache
    const existing = quizService.getSavedQuizzes();
    localStorage.setItem(QUIZ_STORAGE_KEY, JSON.stringify([quiz, ...existing]));

    return quiz;
  },

  getSavedQuizzes(): Quiz[] {
    try {
      const raw = localStorage.getItem(QUIZ_STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  },

  async submitQuiz(submission: QuizSubmission, quiz: Quiz): Promise<QuizResult> {
    let score = 0;
    const details = quiz.questions.map((q) => {
      const selected = submission.answers[q.id];
      const correct = q.correct_index ?? 0;
      const isCorrect = selected === correct;
      if (isCorrect) score += 1;

      return {
        question_id: q.id,
        question: q.question,
        selected_index: selected !== undefined ? selected : -1,
        correct_index: correct,
        is_correct: isCorrect,
        explanation: q.explanation,
      };
    });

    const total = quiz.questions.length;
    const percentage = total > 0 ? Math.round((score / total) * 100) : 0;

    const result: QuizResult = {
      score,
      total_questions: total,
      percentage,
      details,
    };

    const historyItem = {
      quiz_id: quiz.id,
      title: quiz.title,
      topic: quiz.topic,
      difficulty: quiz.difficulty,
      score,
      total,
      percentage,
      timestamp: new Date().toISOString(),
      synced: false,
    };

    // Save to history immediately
    try {
      const history = quizService.getQuizHistory();
      localStorage.setItem(
        QUIZ_HISTORY_KEY,
        JSON.stringify([historyItem, ...history])
      );
    } catch (e) {
      // Ignore
    }

    // Submit to backend
    try {
      await apiClient.post('/analytics/quiz-attempt', {
        quiz_id: quiz.id,
        title: quiz.title,
        topic: quiz.topic,
        difficulty: quiz.difficulty,
        score,
        total_questions: total,
        percentage,
        answers: submission.answers,
        details,
        questions: quiz.questions,
      });

      // Mark as synced in history
      try {
        const history = quizService.getQuizHistory();
        if (history.length > 0 && history[0].quiz_id === quiz.id) {
          history[0].synced = true;
          localStorage.setItem(QUIZ_HISTORY_KEY, JSON.stringify(history));
        }
      } catch (e) {
        // Ignore
      }
    } catch (err) {
      console.warn('Backend quiz attempt sync deferred:', err);
    }

    return result;
  },

  async syncPendingQuizAttempts(): Promise<void> {
    try {
      const history = quizService.getQuizHistory();
      let updated = false;

      for (const item of history) {
        if (!item.synced) {
          try {
            await apiClient.post('/analytics/quiz-attempt', {
              quiz_id: item.quiz_id,
              title: item.title,
              topic: item.topic,
              difficulty: item.difficulty || 'medium',
              score: item.score,
              total_questions: item.total || 1,
              percentage: item.percentage || 0,
            });
            item.synced = true;
            updated = true;
          } catch (e) {
            // Stop syncing if backend unreachable
            break;
          }
        }
      }

      if (updated) {
        localStorage.setItem(QUIZ_HISTORY_KEY, JSON.stringify(history));
      }
    } catch {
      // Ignore
    }
  },

  getQuizHistory(): any[] {
    try {
      const raw = localStorage.getItem(QUIZ_HISTORY_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  },
};

