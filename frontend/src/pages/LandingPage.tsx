import React from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  BookOpen,
  Bot,
  BrainCircuit,
  CheckCircle2,
  FileCheck2,
  FileText,
  GraduationCap,
  HelpCircle,
  Image as ImageIcon,
  Layers,
  Moon,
  ShieldCheck,
  Sparkles,
  Sun,
  TrendingUp,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/common/Button';

export const LandingPage: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  const { isAuthenticated } = useAuth();

  const features = [
    {
      icon: BrainCircuit,
      title: 'Agentic AI Tutor',
      description: 'Adaptive concept breakdown from beginner to advanced with real-world analogies and step-by-step reasoning.',
    },
    {
      icon: BookOpen,
      title: 'Course Material Study',
      description: 'Upload your textbooks, PDFs, and lecture notes. Get precise answers cited directly with page numbers.',
    },
    {
      icon: ImageIcon,
      title: 'Multimodal Vision',
      description: 'Upload complex system diagrams, network topologies, coordinate plots, and handwritten math formulas.',
    },
    {
      icon: HelpCircle,
      title: 'Interactive Quiz Engine',
      description: 'Generate customizable multiple-choice quizzes with detailed pedagogical answer explanations.',
    },
    {
      icon: FileText,
      title: 'Automated Study Summaries',
      description: 'Extract key definitions, revision notes, and exam takeaways from dense academic documents in seconds.',
    },
    {
      icon: TrendingUp,
      title: 'Learning Analytics',
      description: 'Track your weekly study streaks, subject mastery, quiz completion, and question distribution.',
    },
  ];

  const steps = [
    {
      step: '01',
      title: 'Upload Study Materials',
      desc: 'Drop in your course textbooks, PDF notes, or diagram snapshots. AisynEdu parses and indexes every page.',
    },
    {
      step: '02',
      title: 'Engage with Agentic Tutor',
      desc: 'Ask questions, explore derivations, and let the multi-agent router select the ideal pedagogical capability.',
    },
    {
      step: '03',
      title: 'Test and Master Concepts',
      desc: 'Generate targeted quizzes, inspect instant answer explanations, and reinforce weak knowledge areas.',
    },
  ];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col">
      {/* Top Header */}
      <header className="h-20 border-b border-slate-200/80 dark:border-slate-800/80 bg-white/70 dark:bg-slate-900/70 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto h-full px-4 sm:px-6 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-primary-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/25">
              <GraduationCap className="w-6 h-6" />
            </div>
            <div>
              <span className="font-extrabold text-xl tracking-tight text-slate-900 dark:text-white">
                Aisyn<span className="text-primary-600 dark:text-primary-400">Edu</span>
              </span>
            </div>
          </Link>

          <div className="flex items-center gap-3">
            <button
              onClick={toggleTheme}
              aria-label="Toggle Theme"
              className="p-2.5 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              {theme === 'dark' ? (
                <Sun className="w-5 h-5 text-amber-400" />
              ) : (
                <Moon className="w-5 h-5 text-slate-600" />
              )}
            </button>

            {isAuthenticated ? (
              <Link to="/dashboard">
                <Button variant="primary" rightIcon={<ArrowRight className="w-4 h-4" />}>
                  Go to Dashboard
                </Button>
              </Link>
            ) : (
              <>
                <Link to="/login">
                  <Button variant="ghost">Log In</Button>
                </Link>
                <Link to="/register">
                  <Button variant="primary">Get Started</Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-16 pb-20 sm:pt-24 sm:pb-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary-50 dark:bg-primary-950/70 border border-primary-200 dark:border-primary-800 text-xs font-semibold text-primary-700 dark:text-primary-300 mb-8 shadow-sm">
            <Sparkles className="w-4 h-4 text-primary-600 dark:text-primary-400" />
            <span>Learn. Connect. Evolve.</span>
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-slate-900 dark:text-white max-w-4xl mx-auto leading-tight">
            Master Any Subject with Your <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-600 via-indigo-600 to-primary-400">Personalized AI Tutor</span>
          </h1>

          <p className="mt-6 text-lg sm:text-xl text-slate-600 dark:text-slate-300 max-w-2xl mx-auto leading-relaxed">
            AisynEdu is an AI-powered personalized learning platform that helps students understand concepts, generate intelligent study notes, practice quizzes, and learn more effectively.
          </p>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link to="/register">
              <Button size="lg" rightIcon={<ArrowRight className="w-5 h-5" />}>
                Start Learning Free
              </Button>
            </Link>
            <Link to="/login">
              <Button size="lg" variant="outline">
                Sign In to Account
              </Button>
            </Link>
          </div>

          {/* Social Proof */}
          <div className="mt-12 flex flex-wrap items-center justify-center gap-6 text-xs text-slate-500 dark:text-slate-400">
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              <span>Grounded Document Citations</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              <span>Multimodal Vision & Math OCR</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              <span>Gemini & Local AI Support</span>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 bg-white dark:bg-slate-900/60 border-y border-slate-200/80 dark:border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl font-extrabold text-slate-900 dark:text-white">
              Built for Deep Academic Comprehension
            </h2>
            <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">
              Unlike generic chatbots, AisynEdu is engineered specifically for students, researchers, and lifelong learners.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feat, i) => {
              const Icon = feat.icon;
              return (
                <div
                  key={i}
                  className="bg-slate-50 dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow"
                >
                  <div className="w-12 h-12 rounded-xl bg-primary-100 dark:bg-primary-950/80 text-primary-600 dark:text-primary-400 flex items-center justify-center mb-5">
                    <Icon className="w-6 h-6" />
                  </div>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">
                    {feat.title}
                  </h3>
                  <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                    {feat.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* How it Works */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl font-extrabold text-slate-900 dark:text-white">
              How AisynEdu Works
            </h2>
            <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">
              Three simple steps to transform raw textbooks into an interactive learning companion.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {steps.map((st, i) => (
              <div
                key={i}
                className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-8 relative shadow-sm"
              >
                <div className="text-3xl font-black text-primary-600/30 dark:text-primary-400/20 mb-4">
                  {st.step}
                </div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">
                  {st.title}
                </h3>
                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                  {st.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto border-t border-slate-200 dark:border-slate-800 py-8 bg-white dark:bg-slate-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500 dark:text-slate-400">
          <div className="flex items-center gap-2">
            <GraduationCap className="w-4 h-4 text-primary-600" />
            <span className="font-semibold text-slate-800 dark:text-slate-200">AisynEdu</span>
            <span>&copy; {new Date().getFullYear()} All rights reserved.</span>
          </div>
          <div className="flex items-center gap-4">
            <Link to="/login" className="hover:text-primary-600">Login</Link>
            <Link to="/register" className="hover:text-primary-600">Register</Link>
            <span className="text-slate-300 dark:text-slate-700">|</span>
            <span>FastAPI & LangGraph Powered</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

