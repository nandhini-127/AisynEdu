import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Calendar,
  Check,
  Cpu,
  GraduationCap,
  Lock,
  LogOut,
  Mail,
  Moon,
  Save,
  ShieldCheck,
  Sun,
  User as UserIcon,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { authService } from '../services/authService';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { Input } from '../components/common/Input';
import { Badge } from '../components/common/Badge';

export const ProfilePage: React.FC = () => {
  const { user, refreshUser, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const [name, setName] = useState(user?.name || '');
  const [preferredLlm, setPreferredLlm] = useState(user?.preferred_llm || 'gemini');
  const [isSaving, setIsSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setSuccessMessage(null);
    setErrorMessage(null);

    try {
      await authService.updateProfile({
        name,
        preferred_llm: preferredLlm,
      });
      await refreshUser();
      setSuccessMessage('Profile preferences successfully updated.');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.message || 'Failed to update profile.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="space-y-8 pb-12 max-w-3xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
          <UserIcon className="w-6 h-6 text-primary-600" />
          <span>User Profile & Learning Preferences</span>
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Manage your personal account settings, security, and AI study tutor preferences.
        </p>
      </div>

      {successMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-700 dark:text-emerald-300 font-medium flex items-center gap-2">
          <Check className="w-4 h-4" />
          <span>{successMessage}</span>
        </div>
      )}

      {errorMessage && (
        <div className="p-3.5 rounded-xl bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-800 text-xs text-red-700 dark:text-red-300 font-medium">
          {errorMessage}
        </div>
      )}

      {/* Account Overview Card */}
      <Card className="p-6 sm:p-8">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-primary-600 to-indigo-500 text-white flex items-center justify-center font-extrabold text-2xl shadow-lg shadow-indigo-500/20">
              {user?.name ? user.name.charAt(0).toUpperCase() : 'S'}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                  {user?.name || 'Student'}
                </h3>
                <Badge variant={user?.role === 'administrator' ? 'purple' : 'primary'} size="sm">
                  {user?.role === 'administrator' ? 'ADMIN' : 'STUDENT'}
                </Badge>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">{user?.email}</p>
              <p className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                Member since {user?.created_at ? new Date(user.created_at).toLocaleDateString() : '2026'}
              </p>
            </div>
          </div>

          <Button
            variant="danger"
            size="sm"
            onClick={handleLogout}
            leftIcon={<LogOut className="w-4 h-4" />}
          >
            Sign Out
          </Button>
        </div>

        {/* Edit Form */}
        <form onSubmit={handleSaveProfile} className="space-y-5 pt-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Full Name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              leftIcon={<UserIcon className="w-4 h-4" />}
            />

            <Input
              label="Email Address"
              type="email"
              value={user?.email || ''}
              disabled
              helperText="Email cannot be changed."
              leftIcon={<Mail className="w-4 h-4" />}
            />
          </div>

          {/* Preferred LLM Provider */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Default AI Study Engine
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setPreferredLlm('gemini')}
                className={`p-3 rounded-xl border text-left flex items-start gap-3 transition-all ${
                  preferredLlm === 'gemini'
                    ? 'border-primary-500 bg-primary-50/70 dark:bg-primary-950/60 font-semibold'
                    : 'border-slate-200 dark:border-slate-800'
                }`}
              >
                <Cpu className="w-5 h-5 text-primary-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-bold text-slate-900 dark:text-slate-100">
                    Gemini Flash
                  </p>
                  <p className="text-[11px] text-slate-400 font-normal">
                    High speed, multimodal vision, pedagogical step-by-step reasoning.
                  </p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setPreferredLlm('ollama')}
                className={`p-3 rounded-xl border text-left flex items-start gap-3 transition-all ${
                  preferredLlm === 'ollama'
                    ? 'border-emerald-500 bg-emerald-50/70 dark:bg-emerald-950/60 font-semibold'
                    : 'border-slate-200 dark:border-slate-800'
                }`}
              >
                <Cpu className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-bold text-slate-900 dark:text-slate-100">
                    Ollama Local
                  </p>
                  <p className="text-[11px] text-slate-400 font-normal">
                    Local model inference for offline learning and data privacy.
                  </p>
                </div>
              </button>
            </div>
          </div>

          {/* Theme Preference */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Display Theme
            </label>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={toggleTheme}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs font-medium text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
              >
                {theme === 'dark' ? (
                  <>
                    <Sun className="w-4 h-4 text-amber-400" />
                    <span>Dark Theme (Active)</span>
                  </>
                ) : (
                  <>
                    <Moon className="w-4 h-4 text-slate-600" />
                    <span>Light Theme (Active)</span>
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="pt-4 flex justify-end">
            <Button
              type="submit"
              size="md"
              isLoading={isSaving}
              leftIcon={<Save className="w-4 h-4" />}
            >
              Save Preferences
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
};

