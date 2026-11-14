import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Check, Cpu, GraduationCap, Lock, Mail, User, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';

export const RegisterPage: React.FC = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [preferredLlm, setPreferredLlm] = useState('gemini');
  const [role, setRole] = useState<'student' | 'administrator'>('student');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const { register } = useAuth();
  const navigate = useNavigate();

  // Password rules validation
  const hasMinLength = password.length >= 8;
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasDigit = /[0-9]/.test(password);
  const hasSpecial = /[^A-Za-z0-9]/.test(password);
  const isPasswordValid = hasMinLength && hasUpper && hasLower && hasDigit && hasSpecial;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !email || !password) {
      setError('Please fill in all required fields.');
      return;
    }

    if (!isPasswordValid) {
      setError('Password does not meet the security criteria.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await register({
        name,
        email,
        password,
        role,
        preferred_llm: preferredLlm,
      });
      navigate('/dashboard');
    } catch (err: any) {
      const detail =
        err?.response?.data?.message ||
        err?.response?.data?.detail ||
        'Registration failed. Please check your information.';
      setError(detail);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <Link to="/" className="inline-flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-primary-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/25">
            <GraduationCap className="w-7 h-7" />
          </div>
        </Link>
        <h2 className="mt-4 text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
          Create Your AisynEdu Account
        </h2>
        <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
          Learn. Connect. Evolve. — Join the AI-powered personalized learning platform
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-white dark:bg-slate-900 py-8 px-6 shadow-sm border border-slate-200/80 dark:border-slate-800 rounded-2xl sm:px-10">
          {error && (
            <div className="mb-4 p-3 rounded-xl bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-800 text-xs text-red-600 dark:text-red-400 font-medium">
              {error}
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <Input
              label="Full Name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Alex Johnson"
              required
              leftIcon={<User className="w-4 h-4" />}
            />

            <Input
              label="Email Address"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="alex@university.edu"
              required
              leftIcon={<Mail className="w-4 h-4" />}
            />

            <div>
              <Input
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                leftIcon={<Lock className="w-4 h-4" />}
              />
              {/* Password strength checklist */}
              <div className="mt-2.5 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800 text-[11px] space-y-1">
                <div className="flex items-center gap-1.5 font-medium text-slate-500 dark:text-slate-400 mb-1">
                  Password Security Requirements:
                </div>
                <div className="grid grid-cols-2 gap-1 text-slate-600 dark:text-slate-400">
                  <span className={`flex items-center gap-1 ${hasMinLength ? 'text-emerald-600 font-semibold' : ''}`}>
                    {hasMinLength ? <Check className="w-3 h-3" /> : <X className="w-3 h-3 text-slate-400" />} At least 8 chars
                  </span>
                  <span className={`flex items-center gap-1 ${hasUpper ? 'text-emerald-600 font-semibold' : ''}`}>
                    {hasUpper ? <Check className="w-3 h-3" /> : <X className="w-3 h-3 text-slate-400" />} 1 uppercase letter
                  </span>
                  <span className={`flex items-center gap-1 ${hasLower ? 'text-emerald-600 font-semibold' : ''}`}>
                    {hasLower ? <Check className="w-3 h-3" /> : <X className="w-3 h-3 text-slate-400" />} 1 lowercase letter
                  </span>
                  <span className={`flex items-center gap-1 ${hasDigit ? 'text-emerald-600 font-semibold' : ''}`}>
                    {hasDigit ? <Check className="w-3 h-3" /> : <X className="w-3 h-3 text-slate-400" />} 1 number
                  </span>
                  <span className={`flex items-center gap-1 col-span-2 ${hasSpecial ? 'text-emerald-600 font-semibold' : ''}`}>
                    {hasSpecial ? <Check className="w-3 h-3" /> : <X className="w-3 h-3 text-slate-400" />} 1 special symbol (@, #, $, etc.)
                  </span>
                </div>
              </div>
            </div>

            {/* Preferred LLM Provider */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Default AI Study Engine
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setPreferredLlm('gemini')}
                  className={`p-2.5 rounded-xl border text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
                    preferredLlm === 'gemini'
                      ? 'border-primary-500 bg-primary-50 text-primary-700 dark:bg-primary-950/60 dark:text-primary-300'
                      : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400'
                  }`}
                >
                  <Cpu className="w-4 h-4 text-primary-600" />
                  <span>Gemini Flash</span>
                </button>
                <button
                  type="button"
                  onClick={() => setPreferredLlm('ollama')}
                  className={`p-2.5 rounded-xl border text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
                    preferredLlm === 'ollama'
                      ? 'border-emerald-500 bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300'
                      : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400'
                  }`}
                >
                  <Cpu className="w-4 h-4 text-emerald-600" />
                  <span>Ollama Local</span>
                </button>
              </div>
            </div>

            <Button
              type="submit"
              className="w-full mt-4"
              isLoading={isLoading}
              disabled={!isPasswordValid}
            >
              Create Account
            </Button>
          </form>

          <div className="mt-6 text-center text-xs text-slate-500 dark:text-slate-400">
            Already have an account?{' '}
            <Link
              to="/login"
              className="font-semibold text-primary-600 hover:text-primary-500 dark:text-primary-400"
            >
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

